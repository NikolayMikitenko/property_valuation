from __future__ import annotations

import json
from typing import Any

import httpx

from a2a.client import ClientConfig, create_client
from a2a.client.card_resolver import A2ACardResolver

from a2a.client.client import ClientCallContext

from a2a.helpers.proto_helpers import (
    get_artifact_text,
    get_message_text,
    get_stream_response_text,
    new_text_message,
)
from a2a.types import SendMessageRequest
# from a2a.types import Message, Part, Role, SendMessageRequest

def _try_get_text(obj: Any) -> str | None:
    if obj is None:
        return None

    for fn in (get_stream_response_text, get_message_text, get_artifact_text):
        try:
            text = fn(obj)
            if text:
                return text
        except Exception:
            pass

    return None


def _extract_text_from_response(chunk: Any) -> str:
    # 1. direct helper paths
    text = _try_get_text(chunk)
    if text:
        return text

    # 2. common wrapper attrs
    for attr in ("root", "result", "event", "task"):
        child = getattr(chunk, attr, None)
        text = _try_get_text(child)
        if text:
            return text

    # 3. task.status.message
    for candidate in (chunk, getattr(chunk, "root", None), getattr(chunk, "task", None)):
        if candidate is None:
            continue

        status = getattr(candidate, "status", None)
        if status is not None:
            message = getattr(status, "message", None)
            text = _try_get_text(message)
            if text:
                return text

        # 4. task.history[-1]
        history = getattr(candidate, "history", None)
        if history:
            try:
                text = _try_get_text(history[-1])
                if text:
                    return text
            except Exception:
                pass

        # 5. task.artifacts[-1]
        artifacts = getattr(candidate, "artifacts", None)
        if artifacts:
            try:
                text = _try_get_text(artifacts[-1])
                if text:
                    return text
            except Exception:
                pass

    raise RuntimeError(f"Unsupported A2A response type: {type(chunk).__name__}")

async def _call_a2a_agent(base_url: str, payload: dict[str, Any], read_timeout: float = 300.0,) -> dict[str, Any]:
    timeout = httpx.Timeout(
        connect=20.0,
        read=read_timeout,
        write=60.0,
        pool=60.0,
    )

    resolver_httpx_client = httpx.AsyncClient(timeout=timeout)
    transport_httpx_client = httpx.AsyncClient(timeout=timeout)

    # async with httpx.AsyncClient(timeout=timeout) as httpx_client:
    # async with httpx.AsyncClient(timeout=None) as httpx_client:
    try:
        resolver = A2ACardResolver(
            # httpx_client=httpx_client,
            httpx_client=resolver_httpx_client,
            base_url=base_url,
        )
        card = await resolver.get_agent_card()

        client = await create_client(
            agent=card,
            client_config=ClientConfig(
                streaming=False,
                httpx_client=transport_httpx_client,
                ),
        )

        try:
            message = new_text_message(
                text=json.dumps(payload, ensure_ascii=False)
            )
            request = SendMessageRequest(message=message)

            # message = Message(
            #     role=Role.ROLE_USER,
            #     parts=[Part(text=json.dumps(payload, ensure_ascii=False))],
            # )
            # request = SendMessageRequest(message=message)

            call_context = ClientCallContext(timeout=read_timeout)

            last_chunk = None
            async for chunk in client.send_message(request, context=call_context):
                last_chunk = chunk

            if last_chunk is None:
                raise RuntimeError(f"No response from A2A agent at {base_url}")

            text = _extract_text_from_response(last_chunk)
            return json.loads(text)
        finally:
            await client.close()

    finally:
        await resolver_httpx_client.aclose()
        await transport_httpx_client.aclose()

async def call_researcher(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await _call_a2a_agent(base_url, payload, read_timeout=600.0)


async def call_validator(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await _call_a2a_agent(base_url, payload, read_timeout=600.0)


async def call_proof(base_url: str, payload: dict[str, Any]) -> dict[str, Any]:
    return await _call_a2a_agent(base_url, payload, read_timeout=600.0)