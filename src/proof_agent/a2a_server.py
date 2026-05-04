from __future__ import annotations

import asyncio
import json
import logging
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from starlette.applications import Starlette

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

from proof_agent.config import CONFIG
from proof_agent.graph import ProofGraphService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class ProofAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.service = ProofGraphService()
        self.graph = None
        self.graph_lock = asyncio.Lock()
        self.running_tasks: set[str] = set()

    async def _get_graph(self):
        if self.graph is None:
            async with self.graph_lock:
                if self.graph is None:
                    self.graph = await self.service.build_graph()
        return self.graph

    async def warmup(self) -> None:
        logger.info("Proof agent warmup started")
        await self._get_graph()
        logger.info("Proof agent warmup finished")

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or ""
        context_id = context.context_id or ""

        if task_id and task_id in self.running_tasks:
            self.running_tasks.remove(task_id)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )
        await updater.cancel()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task_id = context.task_id or ""
        context_id = context.context_id or ""
        user_message = context.message

        logger.info(
            "PROOF EXECUTE ENTERED task_id=%s context_id=%s raw_input=%s",
            task_id,
            context_id,
            context.get_user_input(),
        )

        if not user_message or not task_id or not context_id:
            logger.warning(
                "PROOF EXECUTE EARLY RETURN task_id=%s context_id=%s user_message=%s",
                task_id,
                context_id,
                bool(user_message),
            )
            return

        self.running_tasks.add(task_id)

        updater = TaskUpdater(
            event_queue=event_queue,
            task_id=task_id,
            context_id=context_id,
        )

        try:
            await event_queue.enqueue_event(
                Task(
                    id=task_id,
                    context_id=context_id,
                    status=TaskStatus(state=TaskState.TASK_STATE_SUBMITTED),
                    history=[user_message],
                )
            )

            await updater.start_work(
                message=updater.new_agent_message(
                    parts=[Part(text="Capturing screenshot...")]
                )
            )

            raw_input = context.get_user_input()
            payload = self._parse_input(raw_input)

            url = payload.get("url")
            if not url:
                await updater.failed(
                    message=updater.new_agent_message(
                        parts=[
                            Part(
                                text=json.dumps(
                                    {"error": "Missing required field: url"},
                                    ensure_ascii=False,
                                )
                            )
                        ]
                    )
                )
                return

            logger.info("Proof agent started task_id=%s url=%s", task_id, url)

            graph = await self._get_graph()

            try:
                logger.info("PROOF BEFORE GRAPH task_id=%s url=%s", task_id, url)                               
                result = await asyncio.wait_for(
                    graph.ainvoke({"url": url}),
                    timeout=240.0,
                )
                logger.info("PROOF AFTER GRAPH task_id=%s result=%s", task_id, result)
            except asyncio.TimeoutError:
                logger.error("Proof graph timeout task_id=%s url=%s", task_id, url)
                await updater.failed(
                    message=updater.new_agent_message(
                        parts=[
                            Part(
                                text=json.dumps(
                                    {
                                        "error": "Proof graph timeout",
                                        "url": url,
                                    },
                                    ensure_ascii=False,
                                )
                            )
                        ]
                    )
                )
                return

            final_payload = result

            if task_id not in self.running_tasks:
                return

            logger.info("PROOF BEFORE ADD_ARTIFACT task_id=%s", task_id)
            await updater.add_artifact(
                parts=[Part(text=json.dumps(final_payload, ensure_ascii=False))],
                name="proof_result",
                last_chunk=True,
            )
            logger.info("PROOF BEFORE COMPLETE task_id=%s", task_id)
            await updater.complete()
            logger.info("PROOF COMPLETED task_id=%s", task_id)

            logger.info("Proof agent finished task_id=%s", task_id)

        except Exception as e:
            logger.exception("Proof agent execution failed task_id=%s", task_id)
            try:
                await updater.failed(
                    message=updater.new_agent_message(
                        parts=[
                            Part(
                                text=json.dumps(
                                    {
                                        "error": type(e).__name__,
                                        "message": str(e),
                                    },
                                    ensure_ascii=False,
                                )
                            )
                        ]
                    )
                )
            except Exception:
                logger.exception(
                    "Failed to send updater.failed for task_id=%s", task_id
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
            return {"url": raw_input.strip()}


def build_agent_card(base_url: str) -> AgentCard:
    skill = AgentSkill(
        id="capture_proof_screenshot",
        name="Capture proof screenshot",
        description="Captures a screenshot of a listing page and returns the stored path.",
        tags=["proof", "screenshot", "minio", "audit"],
        examples=[
            '{"url":"https://dom.ria.com/uk/realty-prodaja-kvartira-kiev-nivki-salyutnaya-ulitsa-34070917.html"}'
        ],
    )

    return AgentCard(
        name="Proof Agent",
        description="Captures and stores screenshots for audit/proof workflows.",
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


def build_app(host: str = "127.0.0.1", port: int = 9103) -> Starlette:
    base_url = f"http://{host}:{port}"
    agent_card = build_agent_card(base_url)
    executor = ProofAgentExecutor()

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
        await executor.warmup()
        yield

    return Starlette(routes=routes, lifespan=lifespan)

if __name__ == "__main__":
    host = getattr(CONFIG, "a2a_host", "127.0.0.1")
    port = getattr(CONFIG, "a2a_port", 9103)

    app = build_app(host=host, port=port)
    uvicorn.run(app, host=host, port=port)