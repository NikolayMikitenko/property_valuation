from __future__ import annotations

from config import settings
from langfuse.langchain import CallbackHandler

from functools import lru_cache
from langfuse import Langfuse, observe, propagate_attributes

from typing import Any

@lru_cache(maxsize=1)
def get_langfuse_client():
    return Langfuse(
        public_key=settings.langfuse_public_key.get_secret_value(),
        secret_key=settings.langfuse_secret_key.get_secret_value(),
        base_url=settings.langfuse_base_url,
    )

def make_langfuse_handler() -> CallbackHandler:
    return CallbackHandler()

def langchain_config(*, user_id: str, session_id: str, tags: list[str] | None = None) -> dict[str, Any]:
    return {
        "callbacks": [make_langfuse_handler()],
        "metadata": {
            "langfuse_user_id": user_id,
            "langfuse_session_id": session_id,
            "langfuse_tags": tags or [],
        },
    }

@observe(name="mas-run", as_type="span")
def start_root_trace(*, user_id: str, session_id: str, tags: list[str] | None = None):
    with propagate_attributes(
        user_id=user_id,
        session_id=session_id,
        tags=tags or [],
        metadata={"project": "homework-12"},
    ):
        return True