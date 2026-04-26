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

from validator_agent.config import CONFIG
from validator_agent.graph import build_graph

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ValidatorAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.graph = build_graph()
        self.running_tasks: set[str] = set()

    # async def _get_graph(self):

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
                parts=[Part(text="Validating candidate...")]
            )
        )

        try:
            raw_input = context.get_user_input()
            payload = self._parse_input(raw_input)

            required_fields = [
                "valuation_property_description",
                "session_id",
                "item_id",
            ]
            missing = [field for field in required_fields if payload.get(field) is None]
            if missing:
                await updater.failed(
                    message=updater.new_agent_message(
                        parts=[Part(text=json.dumps(
                            {
                                "error": "Missing required fields",
                                "missing": missing,
                            },
                            ensure_ascii=False,
                        ))]
                    )
                )
                return

            result = await self.graph.ainvoke(
                {
                    "valuation_property_description": payload["valuation_property_description"],
                    "session_id": payload["session_id"],
                    "item_id": payload["item_id"],
                    "search_url": payload.get("search_url"),
                    "property_id": payload["property_id"],
                    "url": payload["url"],
                }
            )

            if task_id not in self.running_tasks:
                return

            await updater.add_artifact(
                parts=[Part(text=json.dumps(result, ensure_ascii=False))],
                name="validation_result",
                last_chunk=True,
            )
            await updater.complete()

        except Exception as e:
            logger.exception("Validator agent execution failed")
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
            return {"input": raw_input}


def build_agent_card(base_url: str) -> AgentCard:
    skill = AgentSkill(
        id="validate_candidate",
        name="Validate analog candidate",
        description="Validates one candidate analog and returns status, reason and mongo links.",
        tags=["validation", "real-estate", "analogs", "mongo"],
        examples=[
            '{"valuation_property_description":"1-кімнатна квартира у Києві, 48 м²","session_id":"run-1","item_id":"34158750","search_url":"https://dom.ria.com/uk/search/...","property_id":34158750,"url":"https://dom.ria.com/uk/realty-..."}'
        ],
    )

    return AgentCard(
        name="Validator Agent",
        description="Validates candidate analogs against the valuation object.",
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


def build_app(host: str = "127.0.0.1", port: int = 9102) -> Starlette:
    base_url = f"http://{host}:{port}"
    agent_card = build_agent_card(base_url)

    executor = ValidatorAgentExecutor()

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
        agent_card=agent_card,
    )

    routes = []
    routes.extend(create_agent_card_routes(agent_card))
    routes.extend(create_jsonrpc_routes(request_handler, "/"))

    # @asynccontextmanager
    # async def lifespan(app: Starlette):
    #     await executor._get_graph()
    #     yield

    # return Starlette(routes=routes, lifespan=lifespan)
    return Starlette(routes=routes)


if __name__ == "__main__":
    host = getattr(CONFIG, "a2a_host", "127.0.0.1")
    port = getattr(CONFIG, "a2a_port", 9102)

    app = build_app(host=host, port=port)
    uvicorn.run(app, host=host, port=port)