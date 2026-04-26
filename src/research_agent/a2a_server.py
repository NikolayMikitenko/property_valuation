from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import uvicorn
from starlette.applications import Starlette
from contextlib import asynccontextmanager

from a2a.server.agent_execution.agent_executor import AgentExecutor
from a2a.server.agent_execution.context import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.routes import create_agent_card_routes, create_jsonrpc_routes
from a2a.server.tasks.inmemory_task_store import InMemoryTaskStore
from a2a.server.tasks.task_updater import TaskUpdater
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentInterface,
    AgentSkill,
    Part,
    Task,
    TaskState,
    TaskStatus,
)

from research_agent.config import CONFIG
from research_agent.graph import ResearchGraphService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ResearchAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.service = ResearchGraphService()
        self.graph = None
        self.graph_lock = asyncio.Lock()
        self.running_tasks: set[str] = set()

    async def _get_graph(self):
        if self.graph is None:
            async with self.graph_lock:
                if self.graph is None:
                    self.graph = await self.service.build_graph()
        return self.graph

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id
        if task_id and task_id in self.running_tasks:
            self.running_tasks.remove(task_id)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id or "",
            context_id=context.context_id or "",
        )
        await updater.cancel()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_message = context.message
        task_id = context.task_id
        context_id = context.context_id

        if not user_message or not task_id or not context_id:
            return

        self.running_tasks.add(task_id)

        await event_queue.enqueue_event(
            Task(
                id=task_id,
                context_id=context_id,
                status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                history=[user_message],
            )
        )

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )

        await updater.start_work(
            message=updater.new_agent_message(
                parts=[Part(text="Researching candidates...")]
            )
        )

        try:
            raw_input = context.get_user_input()
            payload = self._parse_input(raw_input)

            user_query = payload.get("user_query")
            if not user_query:
                await updater.failed(
                    message=updater.new_agent_message(
                        parts=[Part(text=json.dumps(
                            {"error": "Missing required field: user_query"},
                            ensure_ascii=False,
                        ))]
                    )
                )
                return

            # Важливо: якщо thread_id не передали — беремо task_id.
            # Якщо передали — researcher зможе пам'ятати попередні виклики в тому ж thread.
            thread_id = (
                payload.get("thread_id")
                or payload.get("valuation_run_id")
                or task_id
            )

            graph = await self._get_graph()
            result = await graph.ainvoke(
                {
                    "user_query": user_query,
                },
                config={"configurable": {"thread_id": thread_id}},
            )

            final_payload = {
                "thread_id": thread_id,
                "search_url": result.get("search_url"),
                "candidates_ids": result.get("candidates_ids"),
            }

            if task_id not in self.running_tasks:
                return

            await updater.add_artifact(
                parts=[Part(text=json.dumps(final_payload, ensure_ascii=False))],
                name="research_result",
                last_chunk=True,
            )
            await updater.complete()

        except Exception as e:
            logger.exception("Research agent execution failed")
            await updater.failed(
                message=updater.new_agent_message(
                    parts=[Part(text=json.dumps(
                        {
                            "error": type(e).__name__,
                            "message": str(e),
                        },
                        ensure_ascii=False,
                    ))]
                )
            )
        finally:
            self.running_tasks.discard(task_id)

    @staticmethod
    def _parse_input(raw_input: str | None) -> dict[str, Any]:
        if not raw_input:
            return {}

        try:
            return json.loads(raw_input)
        except json.JSONDecodeError:
            return {"user_query": raw_input.strip()}


def build_agent_card(base_url: str) -> AgentCard:
    skill = AgentSkill(
        id="research_candidates",
        name="Research analog candidates",
        description="Finds DOM.RIA candidates and returns search_url plus candidates_ids.",
        tags=["research", "real-estate", "domria", "analogs"],
        examples=[
            '{"user_query":"1-кімнатна квартира на вул. Андріївська 9, Київ","thread_id":"research:obj-1"}'
        ],
    )

    return AgentCard(
        name="Research Agent",
        description="Researches real-estate analog candidates via DOM.RIA flow.",
        version="0.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        supported_interfaces=[
            AgentInterface(
                protocol_binding="JSONRPC",
                url=base_url,
            )
        ],
        skills=[skill],
    )


def build_app(host: str = "127.0.0.1", port: int = 9101) -> Starlette:
    base_url = f"http://{host}:{port}"
    agent_card = build_agent_card(base_url)

    executor = ResearchAgentExecutor()

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    @asynccontextmanager
    async def lifespan(app: Starlette):
        await executor._get_graph()
        yield

    return Starlette(routes=routes, lifespan=lifespan)


if __name__ == "__main__":
    host = getattr(CONFIG, "a2a_host", "127.0.0.1")
    port = getattr(CONFIG, "a2a_port", 9101)

    app = build_app(host=host, port=port)
    uvicorn.run(app, host=host, port=port)