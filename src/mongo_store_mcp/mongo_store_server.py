from __future__ import annotations

from mongo_store_mcp.config import CONFIG
from mcp.server.fastmcp import FastMCP

from valuation_store_api import utils
from valuation_store_api.schemas import CandidateItem

from typing import Literal, Optional

mcp = FastMCP(
    "valuation_mongo",
    host=CONFIG.mcp_host,
    port=CONFIG.mcp_port
    )


@mcp.tool()
async def register_valuation_run(
    external_object_id: str,
    valuation_description: str,
    target_count: int,
 ) -> dict:
    return await utils.register_run(
        external_object_id=external_object_id,
        valuation_description=valuation_description,
        target_count=target_count,
    )

@mcp.tool()
async def save_candidates(
    valuation_id: str,
    items: list[CandidateItem]
) -> dict:
    return await utils.save_candidates(
        valuation_id=valuation_id,
        items=[item.model_dump() for item in items],
    )

@mcp.tool()
async def get_unprocessed_valuation_candidates(valuation_id: str, limit: int = 1,) -> list[dict]:
    return await utils.get_unprocessed_candidates(valuation_id=valuation_id, limit=limit)

# @mcp.tool()
# async def mark_valuation_candidate_processing(valuation_id: str, item_id: str,) -> dict:
#     return await utils.mark_candidate_processing(valuation_id=valuation_id, item_id=item_id)

@mcp.tool()
async def save_valuation_candidates_result(
    valuation_id: str,
    item_id: str,
    status: Literal["approved", "declined", "error"],
    reason: str = "",
    mongo_id: Optional[str] = None,
    mongo_path: Optional[str] = None,
    is_duplicate: bool = False,
    property_id: Optional[int] = None,
    url: Optional[str] = None,
    payload: Optional[dict] = None,
) -> dict:
    return await utils.save_validation_result(
        valuation_id=valuation_id,
        item_id=item_id,
        status=status,
        reason=reason,
        mongo_id=mongo_id,
        mongo_path=mongo_path,
        is_duplicate=is_duplicate,
        property_id=property_id,
        url=url,
        payload=payload
    )

@mcp.tool()
async def get_valuation_approved_count(valuation_id: str) -> dict:
    return {"approved_count": await utils.get_approved_count(valuation_id=valuation_id)}

@mcp.tool()
async def increment_valuation_search_round(valuation_id: str) -> dict:
    return await utils.increment_search_round(valuation_id=valuation_id)

@mcp.tool()
async def get_approved_without_materialization(valuation_id: str, limit: int = 50) -> list[dict]:
    return await utils.get_approved_without_materialization(valuation_id=valuation_id, limit=limit)

@mcp.tool()
async def mark_candidate_materialized(valuation_id: str, item_id: str) -> dict:
    return await utils.set_candidates_description(valuation_id=valuation_id, item_id=item_id)

@mcp.tool()
async def get_approved_without_proof(valuation_id: str, limit: int = 50) -> list[dict]:
    return await utils.get_approved_without_proof(valuation_id=valuation_id, limit=limit)

@mcp.tool()
async def save_candidate_external_proof_result(
    valuation_id: str,
    item_id: str,
    external_proof_path: Optional[str] = None,
    proof_error: Optional[str] = None
    ) -> dict:
    return await utils.save_external_proof_result(
        valuation_id=valuation_id,
        item_id=item_id,
        external_proof_path=external_proof_path,
        proof_error=proof_error,
    )

@mcp.tool()
async def get_proof_without_minio(valuation_id: str, limit: int = 50) -> list[dict]:
    return await utils.get_proof_without_minio(valuation_id=valuation_id, limit=limit)

@mcp.tool()
async def save_candidate_proof_result(
    valuation_id: str,
    item_id: str,
    proof_path: Optional[str] = None,
) -> dict:
    return await utils.save_proof_result(
        valuation_id=valuation_id,
        item_id=item_id,
        proof_path=proof_path,
    )

@mcp.tool()
async def complete_valuation_run(valuation_id: str) -> dict:
    return await utils.complete_run(valuation_id=valuation_id)


@mcp.tool()
async def get_valuation_result(valuation_id: str | None = None, external_object_id: str | None = None) -> dict:
    return await utils.get_valuation_result(
        valuation_id=valuation_id,
        external_object_id=external_object_id,
    )

if __name__ == "__main__":
    mcp.run(transport="streamable-http")