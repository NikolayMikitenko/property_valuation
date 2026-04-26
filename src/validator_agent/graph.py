import json

from validator_agent.state import AgentState, InputState, OutputState
from validator_agent.config import CONFIG

from fastmcp import Client
from langchain_openai import ChatOpenAI
from langgraph.graph import START, END, StateGraph
import httpx

from validator_agent.schema import PropertyValidationResult
from validator_agent.prompt import VALIDATE_PROPERTY_SYSTEM_PROMPT
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

def parse_mcp_result(result) -> dict:
    if hasattr(result, "data") and isinstance(result.data, dict):
        return result.data

    if hasattr(result, "structured_content") and isinstance(result.structured_content, dict):
        return result.structured_content

    raise ValueError(f"Unexpected MCP result type: {type(result).__name__}")

async def check_duplicate_node(state: AgentState) -> AgentState:
    async with Client(CONFIG.mongo_mcp_url) as client:
        result = await client.call_tool(
            "get_property",
            {
                "session_id": state["session_id"],
                "url": state["url"],
                "property_id": state.get("property_id"),
            },
        )

    payload = parse_mcp_result(result)
    return {"duplicate_check_result": payload}

def route_after_duplicate_check(state: AgentState) -> str:
    duplicate_result = state.get("duplicate_check_result") or {}
    if duplicate_result.get("found"):
        return "finalize_duplicate"
    return "check_cache"

async def check_cache_node(state: AgentState) -> AgentState:
    async with Client(CONFIG.mongo_mcp_url) as client:
        result = await client.call_tool(
            "get_property_from_cache",
            {
                "url": state["url"],
                "property_id": state.get("property_id"),
            },
        )

    payload = parse_mcp_result(result)
    return {"cache_check_result": payload}

def route_after_cache_check(state: AgentState) -> str:
    cache_result = state.get("cache_check_result") or {}
    if cache_result.get("found"):
        return "validate_property"
    return "fetch_from_domria"

async def fetch_from_domria_node(state: AgentState) -> AgentState:
    async with Client(CONFIG.domria_mcp_url) as client:
        if state.get("property_id") is not None:
            result = await client.call_tool(
                "get_object_by_id",
                {
                    "item_id": state["property_id"],
                    "search_url": state["search_url"],
                },
            )

    payload = parse_mcp_result(result)
    return {"property_payload": payload}

def prepare_cached_payload_node(state: AgentState) -> AgentState:
    cache_result = state["cache_check_result"]
    document = cache_result["document"]

    # document may already contain payload
    payload = document.get("payload", document)

    return {"property_payload": payload}

async def validate_property_node(state: AgentState) -> AgentState:
    model = ChatOpenAI(
        base_url=CONFIG.openai_api_base,
        model=CONFIG.openai_lm_model,
        api_key=CONFIG.openai_api_key,
        temperature=0,
        http_client=httpx.Client(verify=False),
        http_async_client=httpx.AsyncClient(verify=False),
    ).with_structured_output(PropertyValidationResult)

    # messages = [
    #     SystemMessage(content="Ти корисний AI асистент"),
    #     HumanMessage(content="Hi"),
    # ]  

    messages = [
        SystemMessage(content=VALIDATE_PROPERTY_SYSTEM_PROMPT),
        HumanMessage(
            content=(
                "Опис майна яке оцінюємо:\n"
                f"{state["valuation_property_description"]}\n\n"
                "Кандидат-аналог (JSON):\n"
                f"{json.dumps(state["property_payload"], ensure_ascii=False, indent=2)}"
            )
        ),
    ]

    response = await model.ainvoke(messages)

    return {"validation_result": response.model_dump()}


    # content = response.content

    # if isinstance(content, list):
    #     text_parts = []
    #     for part in content:
    #         if isinstance(part, dict) and part.get("text"):
    #             text_parts.append(part["text"])
    #         elif hasattr(part, "text"):
    #             text_parts.append(part.text)
    #     content = "".join(text_parts)

    # if not isinstance(content, str):
    #     raise ValueError("LLM returned unsupported content type")

    payload = json.loads(content)
    return {"validation_result": payload}

async def add_property_node(state: AgentState) -> AgentState:
    validation_result = state["validation_result"]
    property_payload = state["property_payload"]

    async with Client(CONFIG.mongo_mcp_url) as client:
        result = await client.call_tool(
            "add_property",
            {
                "session_id": state["session_id"],
                "property_id": state.get("property_id"),
                "url": state.get("url") or property_payload.get("url"),
                "payload": property_payload,
                "status": validation_result["decision"],
                "reason": validation_result.get("reason", ""),
            },
        )

    payload = parse_mcp_result(result)
    return {"add_result": payload}

def finalize_duplicate_node(state: AgentState) -> AgentState:
    duplicate_result = state["duplicate_check_result"]
    document = duplicate_result["document"]

    # mongo_id = document.get("_id")
    status = document.get("status")
    reason = document.get("reason")
    property_payload = document.get("payload")

    return {
        "session_id": state["session_id"],
        "item_id": state["item_id"],
        "property_id": state.get("property_id"),
        "url": state.get("url") or property_payload.get("url"),
        "status": status,
        "reason": reason,
        "mongo_id": duplicate_result["mongo_id"],
        "mongo_path": duplicate_result["path"],
        "is_duplicate": True,
    }

def finalize_node(state: AgentState) -> AgentState:
    add_result = state["add_result"]
    validation_result = state["validation_result"]
    property_payload = state["property_payload"]

    return {
        "session_id": state["session_id"],
        "item_id": state["item_id"],
        "property_id": state.get("property_id"),
        "url": state.get("url") or property_payload.get("url"),
        "status": validation_result["decision"],
        "reason": validation_result["reason"],
        "mongo_id": add_result.get("mongo_id"),
        "mongo_path": add_result.get("path"),
        "is_duplicate": False,
    }

def build_graph():
    graph = StateGraph(
        AgentState,
        input_schema=InputState,
        output_schema=OutputState,
    )

    graph.add_node("check_duplicate", check_duplicate_node)
    graph.add_node("check_cache", check_cache_node)
    graph.add_node("fetch_from_domria", fetch_from_domria_node)
    graph.add_node("prepare_cached_payload", prepare_cached_payload_node)
    graph.add_node("validate_property", validate_property_node)
    graph.add_node("add_property", add_property_node)
    graph.add_node("finalize_duplicate", finalize_duplicate_node)
    graph.add_node("finalize", finalize_node)

    graph.add_edge(START, "check_duplicate")

    graph.add_conditional_edges(
        "check_duplicate",
        route_after_duplicate_check,
        {
            "finalize_duplicate": "finalize_duplicate",
            "check_cache": "check_cache",
        },
    )

    graph.add_conditional_edges(
        "check_cache",
        route_after_cache_check,
        {
            "validate_property": "prepare_cached_payload",
            "fetch_from_domria": "fetch_from_domria",
        },
    )

    graph.add_edge("prepare_cached_payload", "validate_property")
    graph.add_edge("fetch_from_domria", "validate_property")
    graph.add_edge("validate_property", "add_property")
    graph.add_edge("add_property", "finalize")
    graph.add_edge("finalize_duplicate", END)
    graph.add_edge("finalize", END)

    return graph.compile()