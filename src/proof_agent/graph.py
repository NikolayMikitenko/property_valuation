from __future__ import annotations

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.graph import START, END, StateGraph

from proof_agent.config import CONFIG
from proof_agent.state import AgentState, InputState, OutputState

import json
from typing import Any

def parse_mcp_tool_result(result: Any) -> dict[str, Any]:
    if not isinstance(result, list) or not result:
        return {
            "path": None,
            "error": f"Unexpected MCP result type: {type(result).__name__}",
        }

    first_item = result[0]

    if not isinstance(first_item, dict):
        return {
            "path": None,
            "error": f"Unexpected MCP result item type: {type(first_item).__name__}",
        }

    text = first_item.get("text")
    if not text:
        return {
            "path": None,
            "error": "MCP result does not contain text payload",
        }

    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            "path": None,
            "error": f"Failed to parse MCP JSON payload: {exc}",
        }

class ProofGraphService:
    def __init__(self) -> None:
        self.mcp_client: MultiServerMCPClient | None = None
        self.screenshot_tool = None
        self.graph = None

    async def load_mcp_tools(self):
        if self.screenshot_tool is not None:
            return self.screenshot_tool

        self.mcp_client = MultiServerMCPClient(
            {
                "screenshot": {
                    "transport": "streamable_http",
                    "url": CONFIG.screenshot_mcp_url,
                },
            }
        )

        tools = await self.mcp_client.get_tools()

        self.screenshot_tool = next(
            tool for tool in tools if tool.name == "capture_website_screenshot_to_minio"
        )
        return self.screenshot_tool        

    async def call_screenshot_tool_node(self, state: AgentState) -> AgentState:
        tool = await self.load_mcp_tools()

        result = await tool.ainvoke(
            {
                "url": state["url"],
            }
        )

        parsed = parse_mcp_tool_result(result)
        return {"screenshot_result": parsed}

    @staticmethod
    def finalize_node(state: AgentState) -> AgentState:
        screenshot_result = state.get("screenshot_result") or {}

        if screenshot_result.get("path"):
            return {
                "url": state["url"],
                "path": screenshot_result["path"],
            }

        return {
            "url": state["url"],
            "path": None,
            "error": screenshot_result.get("error", "Screenshot failed"),
            "status_code": screenshot_result.get("status_code"),
        }

    async def build_graph(self):
        if self.graph is not None:
            return self.graph

        await self.load_mcp_tools()

        graph = StateGraph(
            AgentState,
            input_schema=InputState,
            output_schema=OutputState,
        )

        graph.add_node("call_screenshot_tool", self.call_screenshot_tool_node)
        graph.add_node("finalize", self.finalize_node)

        graph.add_edge(START, "call_screenshot_tool")
        graph.add_edge("call_screenshot_tool", "finalize")
        graph.add_edge("finalize", END)

        self.graph = graph.compile()
        return self.graph