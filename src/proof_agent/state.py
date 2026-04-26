from typing import Optional, TypedDict

class InputState(TypedDict, total=False):
    url: str

class AgentState(TypedDict, total=False):
    url: str
    screenshot_result: Optional[dict]

class OutputState(TypedDict, total=False):
    url: str
    path: str | None
    error: str | None
    status_code: str | None