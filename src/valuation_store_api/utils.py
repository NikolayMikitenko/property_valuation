from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4
import hashlib
import uuid
from typing import Any

# from valuation_store_api.schemas import 
from valuation_store_api.db import (
    valuation_objects,
    valuation_candidates,
    )

from bson import ObjectId

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

async def register_run(*, external_object_id: str, valuation_description: str, target_count: int) -> dict:
    now = utcnow()
    valuation_id = str(uuid4())

    await valuation_objects.insert_one(
        {
            "valuation_id": valuation_id,
            "external_object_id": external_object_id,
            "valuation_description": valuation_description,
            "target_count": target_count,
            "search_round": 0,
            "approved_count": 0,
            "status": "running",
            "created_at": now,
            "updated_at": now,
        }
    )

    return {
        "valuation_id": valuation_id,
        "status": "running",
    }

def build_item_id(item: dict[str, Any]) -> str:
    source = item["source"]

    property_id = item.get("property_id")
    if property_id is not None:
        return f"{source}:{property_id}"

    url = item.get("url")
    if url:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()
        return f"{source}:url:{digest}"

    return f"{source}:uuid:{uuid.uuid4()}"

async def save_candidates(*, valuation_id: str, items: list[dict]) -> dict:
    now = utcnow()
    inserted = 0

    for item in items:
        item_id = build_item_id(item)
        doc = {
            "valuation_id": valuation_id,
            "item_id": item_id,
            "property_id": item.get("property_id"),
            "url": item.get("url"),
            "search_url": item.get("search_url"),
            "source": item.get("source"),
            "status": "new",
            "decision": None,
            "reason": None,
            "mongo_id": None,
            "mongo_path": None,
            "is_duplicate": False,
            "description_materialized": False,
            "has_proof": False,
            "external_proof_path": None,
            "proof_error": None,
            "proof_moved": False,
            "proof_path": None,
            "created_at": now,
            "updated_at": now,
        }

        result = await valuation_candidates.update_one(
            {"valuation_id": valuation_id, "item_id": item_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1

    return {"inserted": inserted}

def to_jsonable(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat()

    if isinstance(value, dict):
        return {k: to_jsonable(v) for k, v in value.items()}

    if isinstance(value, list):
        return [to_jsonable(v) for v in value]

    return value

async def get_unprocessed_candidates(*, valuation_id: str, limit: int = 1) -> list[dict]:
    cursor = valuation_candidates.find(
        {"valuation_id": valuation_id, "status": "new"}
    ).sort("created_at", 1).limit(limit)
    docs =  [doc async for doc in cursor]
    return [to_jsonable(doc) for doc in docs]

# async def mark_candidate_processing(*, valuation_id: str, item_id: str) -> dict:
#     await valuation_analog_candidates.update_one(
#         {"valuation_id": valuation_id, "item_id": item_id},
#         {"$set": {"status": "processing", "updated_at": utcnow()}},
#     )
#     return {"ok": True}


async def save_validation_result(
    *,
    valuation_id: str,
    item_id: str,
    status: str,
    reason: str,
    mongo_id: str | None,
    mongo_path: str | None,
    is_duplicate: bool,
    property_id: int | None,
    url: str | None,
    payload: dict | None
) -> dict:
    now = utcnow()
    await valuation_candidates.update_one(
        {"valuation_id": valuation_id, "item_id": item_id},
        {
            "$set": {
                "status": status,
                "reason": reason,
                "mongo_id": mongo_id,
                "mongo_path": mongo_path,
                "is_duplicate": is_duplicate,
                "property_id": property_id,
                "url": url,
                "payload": payload,
                "updated_at": now,
            }
        },
    )

    if status == "approved":
        await valuation_objects.update_one(
            {"valuation_id": valuation_id},
            {"$inc": {"approved_count": 1}, "$set": {"updated_at": now}},
        )

    return {"ok": True}

async def get_approved_count(*, valuation_id: str) -> int:
    # run = await valuation_objects.find_one({"valuation_id": valuation_id}, {"approved_count": 1})
    # return int((run or {}).get("approved_count", 0))
    return await valuation_candidates.count_documents(
        {
            "valuation_id": valuation_id,
            "status": "approved",
        }
    )

async def increment_search_round(*, valuation_id: str) -> dict:
    await valuation_objects.update_one(
        {"valuation_id": valuation_id},
        {"$inc": {"search_round": 1}, "$set": {"updated_at": utcnow()}},
    )
    return {"ok": True}

async def get_approved_without_materialization(*, valuation_id: str, limit: int = 50) -> list[dict]:
    cursor = valuation_candidates.find(
        {
            "valuation_id": valuation_id,
            "status": "approved",
            "description_materialized": False,
        }
    ).limit(limit)
    return [doc async for doc in cursor]

async def set_candidates_description(*, valuation_id: str, item_id: str, payload) -> dict:
    await valuation_candidates.update_one(
        {"valuation_id": valuation_id, "item_id": item_id},
        {"$set": {"description_materialized": True, "payload": payload,"updated_at": utcnow()}},
    )
    return {"ok": True}

async def get_approved_without_proof(*, valuation_id: str, limit: int = 50) -> list[dict]:
    cursor = valuation_candidates.find(
        {
            "valuation_id": valuation_id,
            "status": "approved",
            "has_proof": False,
        }
    ).limit(limit)
    # return [doc async for doc in cursor]
    docs =  [doc async for doc in cursor]
    return [to_jsonable(doc) for doc in docs]

async def save_external_proof_result(*, valuation_id: str, item_id: str, external_proof_path: str | None, proof_error: str | None = None) -> dict:
    await valuation_candidates.update_one(
        {"valuation_id": valuation_id, "item_id": item_id},
        {
            "$set": {
                "external_proof_path": external_proof_path,
                "proof_error": proof_error,
                "has_proof": bool(external_proof_path),
                "updated_at": utcnow(),
            }
        },
    )

    return {"ok": True}

async def get_proof_without_minio(*, valuation_id: str, limit: int = 50) -> list[dict]:
    cursor = valuation_candidates.find(
        {
            "valuation_id": valuation_id,
            "status": "approved",
            "has_proof": True,
            "proof_moved": False,
        }
    ).limit(limit)
    # return [doc async for doc in cursor]  
    docs =  [doc async for doc in cursor]
    return [to_jsonable(doc) for doc in docs]

async def save_proof_result(*, valuation_id: str, item_id: str, proof_path: str | None) -> dict:
    await valuation_candidates.update_one(
        {"valuation_id": valuation_id, "item_id": item_id},
        {
            "$set": {
                "proof_path": proof_path,
                "proof_moved": bool(proof_path),
                "updated_at": utcnow(),
            }
        },
    )
    return {"ok": True}

async def complete_run(*, valuation_id: str) -> dict:
    await valuation_objects. update_one(
        {"valuation_id": valuation_id},
        {"$set": {"status": "completed", "updated_at": utcnow()}},
    )
    return {"ok": True}

async def get_valuation_result(*, valuation_id: str | None = None, external_object_id: str | None = None) -> dict:
    run_query = {}
    if valuation_id:
        run_query["valuation_id"] = valuation_id
    elif external_object_id:
        run_query["external_object_id"] = external_object_id
    else:
        raise ValueError("Either valuation_id or external_object_id is required")

    run = await valuation_objects.find_one(run_query)
    if not run:
        return {"found": False}

    candidates = [doc async for doc in valuation_candidates.find({"valuation_id": run["valuation_id"]})]

    return {
        "found": True,
        "valuation_id": run["valuation_id"],
        "external_object_id": run["external_object_id"],
        "valuation_description": run["valuation_description"],
        "target_count": run["target_count"],
        "approved_count": run["approved_count"],
        "status": run["status"],
        "created_at": run["created_at"],
        "updated_at": run["updated_at"],
        "candidates": candidates
    }