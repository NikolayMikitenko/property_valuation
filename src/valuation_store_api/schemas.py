from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

class RegisterRunRequest(BaseModel):
    external_object_id: str
    # object_name: str
    valuation_description: str
    target_count: int

# class RegisterRunResponse(BaseModel):
#     valuation_run_id: str
#     external_object_id: str
#     object_name: str
#     target_count: int
#     status: str

class CandidateItem(BaseModel):
    # item_id: str
    property_id: Optional[int] = None
    url: Optional[str] = None
    search_url: Optional[str] = None
    source: str = "domria"

class SaveCandidatesRequest(BaseModel):
    valuation_id: str
    items: list[CandidateItem]

class ValidationPatchRequest(BaseModel):
    valuation_id: str
    item_id: str
    status: Literal["approved", "declined", "error"]
    reason: str = ""
    mongo_id: Optional[str] = None
    mongo_path: Optional[str] = None
    is_duplicate: bool = False
    property_id: Optional[int] = None
    url: Optional[str] = None

class ProofPatchRequest(BaseModel):
    valuation_id: str
    item_id: str
    external_proof_path: Optional[str] = None
    proof_error: Optional[str] = None

class MinioPatchRequest(BaseModel):
    valuation_id: str
    item_id: str
    proof_path: Optional[str] = None

# class RunResultResponse(BaseModel):
#     valuation_run_id: str
#     external_object_id: str
#     object_name: str
#     valuation_description: str
#     target_count: int
#     approved_count: int
#     status: str
#     candidates: list[dict] = Field(default_factory=list)