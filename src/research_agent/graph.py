from langgraph.graph import START, END, StateGraph
from research_agent.state import AgentState, InputState, OutputState
from research_agent.config import CONFIG
from research_agent.prompts import (
    DETECT_ASSET_KIND_PROMPT,
    DETECT_PROPERTY_TYPE_PROMPT,
    DETECT_PROPERTY_SUBTYPE_PROMPT,
    PREPARE_LOCATION_ADDRESS,
    SELECT_DOMRIA_OBJECT_LOCATION_PROMPT,
    SELECT_DOMRIA_CANDIDATES,
)

from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import InMemorySaver
import httpx
from typing import Any

from research_agent.schema import (
    DetectAssetKindResult,
    DetectPropertyTypeResult,
    DetectPropertySubtypeResult,
    OBJECTS,
    SelectDomRiaObjectLocationResult,
    SEARCH_LEVEL_NEXT
)

from langchain_core.messages import SystemMessage, HumanMessage

from fastmcp import Client
import json

from langchain_mcp_adapters.client import MultiServerMCPClient

# def parse_mcp_result(result):
#     if hasattr(result, "data") and isinstance(result.data, dict):
#         return result.data

#     if hasattr(result, "structured_content") and isinstance(result.structured_content, dict):
#         return result.structured_content
    
#     if hasattr(result, "text"):
#         return result.text

#     raise ValueError(f"Unexpected MCP result type: {type(result).__name__}")

def parse_mcp_result(result: Any) -> dict[str, Any]:
    # 1. Already parsed dict
    if isinstance(result, dict):
        return result

    # 2. JSON string
    if isinstance(result, str):
        try:
            parsed = json.loads(result)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        raise ValueError(f"String result is not valid JSON object: {result!r}")

    # 3. List of content blocks like:
    # [{"type": "text", "text": "{\"search_url\": ... }"}]
    if isinstance(result, list):
        if not result:
            raise ValueError("MCP result is an empty list")

        first = result[0]

        if isinstance(first, dict):
            # direct dict payload inside list
            if "text" in first and isinstance(first["text"], str):
                try:
                    parsed = json.loads(first["text"])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass

            # if first element itself is already useful dict payload
            return first

        raise ValueError(f"Unexpected list item type in MCP result: {type(first).__name__}")

    # 4. MCP result object with .data
    if hasattr(result, "data"):
        data = getattr(result, "data")
        if isinstance(data, dict):
            return data
        if isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    # 5. MCP result object with .structured_content
    if hasattr(result, "structured_content"):
        structured_content = getattr(result, "structured_content")
        if isinstance(structured_content, dict):
            return structured_content
        if isinstance(structured_content, str):
            try:
                parsed = json.loads(structured_content)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    # 6. MCP result object with .content
    if hasattr(result, "content"):
        content = getattr(result, "content")

        if isinstance(content, list) and content:
            first = content[0]

            if isinstance(first, dict) and "text" in first and isinstance(first["text"], str):
                try:
                    parsed = json.loads(first["text"])
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass

            if hasattr(first, "text") and isinstance(first.text, str):
                try:
                    parsed = json.loads(first.text)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    pass

        elif isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    # 7. MCP result object with .text
    if hasattr(result, "text"):
        text = getattr(result, "text")
        if isinstance(text, str):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass

    raise ValueError(
        f"Unexpected MCP result type: {type(result).__name__}. Value: {result!r}"
    )


class ResearchGraphService:
    def __init__(self) -> None:
        self.mcp_client: MultiServerMCPClient | None = None
        self.all_mcp_tools: list[Any] = []
        self.checkpointer = InMemorySaver()
        self.graph = None

    def get_llm(self, output_type=None):
        llm = ChatOpenAI(
            base_url=CONFIG.openai_api_base,
            model=CONFIG.openai_lm_model,
            api_key=CONFIG.openai_api_key,
            temperature=0,
            http_client=httpx.Client(verify=False),
            http_async_client=httpx.AsyncClient(verify=False),
            )
        
        return llm if output_type is None else llm.with_structured_output(output_type)

    async def load_mcp_tools(self) -> list[Any]:

        self.mcp_client = MultiServerMCPClient(
            {
                "domria": {
                    "transport": "http",
                    "url": CONFIG.domria_mcp_url,
                }
            }
        )
        self.all_mcp_tools = await self.mcp_client.get_tools()
        return self.all_mcp_tools

    @staticmethod
    def filter_tools_by_name(tools: list[Any], *allowed_names: str) -> list[Any]:
        allowed = set(allowed_names)
        return [tool for tool in tools if tool.name in allowed]

    @staticmethod
    def route_from_start(state: AgentState) -> str:
        if state.get("status") == "exit_founded_all_possible_items":
            return "END"

        if state.get("asset_kind") == "equipment":
            return "equipment_stub"
        
        if state.get("city_id") is not None:
            return "search_domria_candidates"
        
        if state.get("address"):
            return "detect_domria_object_location"

        if state.get("property_subtype"):
            return "create_address"

        if state.get("property_type"):
            return "detect_property_subtype"

        if state.get("asset_kind"):
            return "detect_property_type"

        return "detect_asset_kind"
    
    async def detect_asset_kind_node(self, state: AgentState) -> dict[str, Any]:
        llm = self.get_llm(DetectAssetKindResult)
        result = await llm.ainvoke(
            [
                SystemMessage(content=DETECT_ASSET_KIND_PROMPT),
                HumanMessage(content=state["user_query"]),
            ]
        )

        return {
            "asset_kind": result.asset_kind,
            "status": "asset_kind_detected",
        }  

    @staticmethod
    def route_after_asset_kind(state: AgentState) -> str:
        if state.get("asset_kind") == "equipment":
            return "equipment_stub"
        return "detect_property_type"

    async def equipment_stub_node(self, state: AgentState) -> dict[str, Any]:
        return {
            "property_type": "equipment",
            "property_subtype": "equipment",
            "status": "property_subtype_detected",
        }

    async def detect_property_type_node(self, state: AgentState) -> dict[str, Any]:
        llm = self.get_llm(DetectPropertyTypeResult)
        result = await llm.ainvoke(
            [
                SystemMessage(content=DETECT_PROPERTY_TYPE_PROMPT),
                HumanMessage(content=state["user_query"]),
            ]
        )

        return {
            "property_type": result.property_type,
            "status": "property_type_detected",
        }
    
    async def detect_property_subtype_node(self, state: AgentState) -> dict[str, Any]:
        llm = self.get_llm(DetectPropertySubtypeResult)
        property_type = state["property_type"]

        property_subtypes = OBJECTS[property_type]

        if len(property_subtypes) == 1:
            property_subtype = property_subtypes[0]
        else:
            result = await llm.ainvoke(
                [
                    SystemMessage(content=DETECT_PROPERTY_SUBTYPE_PROMPT),
                    HumanMessage(
                        content=(
                            f"property_type: {property_type}\n\n"
                            f"description:\n{state['user_query']}\n\n"
                            f"available subtypes:\n{property_subtypes}"
                        )
                    ),
                ]
            )
            property_subtype = result.property_subtype

        return {
            "property_subtype": property_subtype,
            "status": "property_subtype_detected",
        }

    async def create_address_node(self, state: AgentState) -> dict[str, Any]:
        llm = self.get_llm()
        result = await llm.ainvoke(
            [
                SystemMessage(content=PREPARE_LOCATION_ADDRESS),
                HumanMessage(content=state["user_query"]),
            ]
        )

        return {
            "address": result.text,
            "status": "address_created",
        }

    async def detect_domria_object_location_node(self, state: AgentState) -> dict[str, Any]:
        async with Client(CONFIG.domria_mcp_url) as client:
            result = await client.call_tool(
                "get_address_ids",
                {
                    "address": state["address"],
                },
            )

        payload = json.loads(result.content[0].text)

        candidates: list[dict[str, Any]] = []
        for item in payload:
            raw_payload = item.get("raw", {}).get("payload", {})
            center = item.get("center", {})

            candidates.append(
                {
                    "group": item.get("group"),
                    "label": item.get("label"),
                    "output": item.get("output"),
                    "similarity": item.get("similarity"),
                    "increasePosition": item.get("increasePosition"),
                    "payload": {
                        "id": raw_payload.get("id"),
                        "cityId": raw_payload.get("cityId"),
                        "stateId": raw_payload.get("stateId"),
                        "name": raw_payload.get("name"),
                        "cityName": raw_payload.get("cityName"),
                    },
                    "longitude": str(center.get("lng")),
                    "latitude": str(center.get("lat")),
                }
            )

        llm = self.get_llm(SelectDomRiaObjectLocationResult)
        selection = await llm.ainvoke(
            [
                SystemMessage(content=SELECT_DOMRIA_OBJECT_LOCATION_PROMPT),
                HumanMessage(
                    content=(
                        f"Адреса: {state['address']}\n\n"
                        f"Кандидати:\n{candidates}"
                    )
                ),
            ]
        )

        street_id = selection.street_id
        if selection.type == "building" and selection.building_id is not None:
            if "_" in selection.building_id and street_id is None:
                street_id = int(selection.building_id.split("_")[0])

        return {
            "building_id": selection.building_id,
            "street_id": street_id,
            "city_id": selection.city_id,
            "state_id": selection.state_id,
            "longitude": selection.longitude,
            "latitude": selection.latitude,
            "status": "DOMRIA_address_ids_detected",
        }

        # 1-кімнатна квартира на вул Андріївська буд 9 в м. Київ, Київська область

    # @staticmethod
    # def merge_candidate_ids(
    #     existing_ids: list[int] | None,
    #     new_ids: list[int] | None,
    # ) -> tuple[list[int], list[int]]:
    #     existing_set = set(existing_ids or [])
    #     new_set = set(new_ids or [])

    #     merged_set = existing_set | new_set
    #     truly_new = new_set - existing_set

    #     return list(merged_set), list(truly_new)

    async def search_domria_candidates_node(self, state: AgentState) -> dict[str, Any]:

        filtered_tools = self.filter_tools_by_name(self.all_mcp_tools, "search_objects")

        llm_with_tools = self.get_llm().bind_tools(filtered_tools)

        search_level = None
        if state.get("search_level") is None:
            search_level = "building"
        elif state.get("search_level") == "city_30":
            return {"status":"exit_founded_all_possible_items"}
        else:
            search_level = SEARCH_LEVEL_NEXT[state["search_level"]]

        result = await llm_with_tools.ainvoke(
            [
                SystemMessage(content=SELECT_DOMRIA_CANDIDATES),
                HumanMessage(content=(
                    f"Property description:\n{state['user_query']}\n\n"
                    f"object_key={state['property_subtype']}\n"
                    f"Search level: {search_level}\n\n"
                    f"Address identifiers:\n"
                    f"building_id={state['building_id']}\n"
                    f"street_id={state['street_id']}\n"
                    f"city_id={state['city_id']}\n"
                    f"state_id={state['state_id']}\n"
                ))
            ]
        )
        
        if not result.tool_calls:
            return {
                "status": "no_tool_call",
                "candidates_ids": [],
            }

        tool_call = result.tool_calls[0]
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]

        tools_by_name = {tool.name: tool for tool in filtered_tools}
        tool = tools_by_name[tool_name]
        tool_result = await tool.ainvoke(tool_args)
        tool_json_result = parse_mcp_result(tool_result)

        new_candidates_ids = tool_json_result.get("items_ids", [])
        all_candidates_ids = state.get("all_candidates_ids", [])
        candidates_ids  = list(set(new_candidates_ids) - set(all_candidates_ids))
        all_candidates_ids = list(set(all_candidates_ids) | set(candidates_ids))

        return {
            "search_level": search_level,
            "search_url": tool_json_result.get("search_url"),
            "all_candidates_ids": all_candidates_ids,
            "candidates_ids": candidates_ids,
            "source": "domria",
            "status": "DOMRIA_candidates_found",
        }

    @staticmethod
    def route_after_search_domria_candidates(state: AgentState) -> str:
        candidates_ids = state.get("candidates_ids", [])

        if len(candidates_ids) > 0:
            return "END"

        current_level = state.get("search_level")
        if current_level == "city_30":
            return "END"

        return "search_domria_candidates"

    async def build_graph(self):
        await self.load_mcp_tools()

        graph = StateGraph(
            AgentState,
            input_schema=InputState,
            output_schema=OutputState,
        )

        graph.add_node("detect_asset_kind", self.detect_asset_kind_node)
        graph.add_node("detect_property_type", self.detect_property_type_node)
        graph.add_node("detect_property_subtype", self.detect_property_subtype_node)
        graph.add_node("equipment_stub", self.equipment_stub_node)
        graph.add_node("create_address", self.create_address_node)
        graph.add_node("detect_domria_object_location", self.detect_domria_object_location_node)
        graph.add_node("search_domria_candidates", self.search_domria_candidates_node)

        graph.add_conditional_edges(
            START,
            self.route_from_start,
            {
                "detect_asset_kind": "detect_asset_kind",
                "detect_property_type": "detect_property_type",
                "detect_property_subtype": "detect_property_subtype",
                "create_address": "create_address",
                "detect_domria_object_location": "detect_domria_object_location",
                "search_domria_candidates": "search_domria_candidates",

                "equipment_stub": "equipment_stub",
                "END": END,
            },
        )

        graph.add_conditional_edges(
            "detect_asset_kind",
            self.route_after_asset_kind,
            {
                "equipment_stub": "equipment_stub",
                "detect_property_type": "detect_property_type",
            },
        )

        graph.add_edge("equipment_stub", END)
        graph.add_edge("detect_property_type", "detect_property_subtype")
        graph.add_edge("detect_property_subtype", "create_address")
        graph.add_edge("create_address", "detect_domria_object_location")
        graph.add_edge("detect_domria_object_location", "search_domria_candidates")
        # graph.add_edge("search_domria_candidates", END)
        graph.add_conditional_edges(
            "search_domria_candidates",
            self.route_after_search_domria_candidates,
            {
                "search_domria_candidates": "search_domria_candidates",
                "END": END,
            },
        )

        self.graph = graph.compile(checkpointer=self.checkpointer)
        return self.graph