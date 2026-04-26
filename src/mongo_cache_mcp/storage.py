from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import DuplicateKeyError

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from mongo_cache_mcp.config import CONFIG

def get_mongo_client() -> MongoClient:
    return MongoClient(CONFIG.mongo_uri)

def get_database(client: MongoClient) -> Database:
    return client[CONFIG.mongo_db_name]

def get_collection(db: Database) -> Collection:
    return db[CONFIG.mongo_collection_name]

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

def build_expires_at() -> datetime:
    return utcnow() + timedelta(seconds=CONFIG.cache_ttl_seconds)

def serialize_document(document: dict[str, Any]) -> dict[str, Any]:
    serialized = dict(document)
    serialized["_id"] = str(serialized["_id"])

    for key in ("created_at", "updated_at", "expires_at"):
        value = serialized.get(key)
        if isinstance(value, datetime):
            serialized[key] = value.isoformat()

    return serialized

def find_by_session_and_property_id(collection: Collection, session_id: str, property_id: int) -> Optional[dict[str, Any]]:
    return collection.find_one({"session_id": session_id, "property_id": property_id})

def find_by_session_and_url(collection: Collection, session_id: str, url: str) -> Optional[dict[str, Any]]:
    return collection.find_one({"session_id": session_id, "url": url})

def find_session_property(
    collection: Collection,
    session_id: str,
    property_id: int | None = None,
    url: str | None = None,
) -> Optional[dict[str, Any]]:
    if property_id is not None:
        document = find_by_session_and_property_id(collection, session_id, property_id)
        if document is not None:
            return document
    
    if url is not None:
        document = find_by_session_and_url(collection, session_id, url)
        if document is not None:
            return document

    return None

def find_by_property_id(collection: Collection, property_id: int) -> Optional[dict[str, Any]]:
    return collection.find_one({"property_id": property_id})

def find_by_url(collection: Collection, url: str) -> Optional[dict[str, Any]]:
    return collection.find_one({"url": url})

def find_property(
    collection: Collection,
    url: str | None = None,
    property_id: int | None = None,
) -> Optional[dict[str, Any]]:
    if property_id is not None:
        document = find_by_property_id(collection, property_id)
        if document is not None:
            return document
        
    if url is not None:
        document = find_by_url(collection, url)
        if document is not None:
            return document

    return None

def insert_property(
    collection: Collection,
    session_id: str,
    property_id: int | None,
    url: str,
    payload: dict[str, Any],
    status: str,
    reason: str
) -> dict[str, Any]:
    now = utcnow()
    expires_at = build_expires_at()

    document = {
        "session_id": session_id,
        "property_id": property_id,
        "url": url,
        "status": status,
        "reason": reason,
        "payload": payload,
        "created_at": now,
        "updated_at": now,
        "expires_at": expires_at,
    }

    try:
        insert_result = collection.insert_one(document)
        mongo_id = str(insert_result.inserted_id)
        return {
            "mongo_id": mongo_id,
            # "created": True,
            "path": f"{CONFIG.mongo_collection_name}/{mongo_id}",
        }
    except DuplicateKeyError:
        existing = collection.find_one({"session_id": session_id, "property_id": property_id})
        if existing is None:
            raise

        mongo_id = str(existing["_id"])
        collection.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "session_id": session_id,
                    "property_id": property_id,
                    "url": url,
                    "payload": payload,
                    "updated_at": now,
                    "expires_at": expires_at,
                }
            },
        )

        return {
            "mongo_id": mongo_id,
            # "created": False,
            "path": f"{CONFIG.mongo_collection_name}/{mongo_id}",
        }
    
# def get_property_by_mongo_id(collection: Collection, mongo_id: str) -> Optional[dict[str, Any]]:
#     return collection.find_one({"_id": ObjectId(mongo_id)})