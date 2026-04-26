from typing import Optional, TypedDict

class InputState(TypedDict, total=False):
    valuation_property_description: str

    session_id: str
    item_id: str
    search_url: Optional[str]
    property_id: Optional[int]
    url: Optional[str]

class AgentState(TypedDict, total=False):
    valuation_property_description: str

    session_id: str
    item_id: str
    search_url: Optional[str]
    property_id: Optional[int]
    url: Optional[str]

    duplicate_check_result: Optional[dict]
    cache_check_result: Optional[dict]
    property_payload: Optional[dict]
    validation_result: Optional[dict]
    add_result: Optional[dict]
    # final: Optional[dict]

class OutputState(TypedDict):
    session_id: str
    item_id: str
    property_id: int | None
    url: str | None
    status: str
    reason: str
    mongo_id: str | None
    mongo_path: str | None
    is_duplicate: bool
    property_payload: dict | None