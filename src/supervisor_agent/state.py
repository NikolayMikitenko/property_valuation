from __future__ import annotations

from typing import Any, Optional, TypedDict


class InputState(TypedDict):
    external_object_id: str
#     object_name: str
    valuation_description: str
    target_count: int


class AgentState(TypedDict, total=False):
    external_object_id: str
#     object_name: str
    valuation_description: str
    target_count: int

    valuation_id: str
    # candidates_batch: list[dict]
    approved_count: int
    search_round: int

#     search_url: Optional[str]
#     candidate_ids: list[int]

    next_candidate: Optional[dict[str, Any]]
#     validation_result: Optional[dict[str, Any]]

#     approved_without_materialization: list[dict[str, Any]]
#     approved_without_proof: list[dict[str, Any]]
#     proof_without_minio: list[dict[str, Any]]

    final: Optional[dict[str, Any]]
    status: str

class OutputState(TypedDict):
    external_object_id: str
    valuation_description: str
    target_count: int

    valuation_id: str | None
    approved_count: int | None

    final: Optional[dict[str, Any]]
    status: str