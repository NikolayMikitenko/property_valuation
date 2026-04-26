from fastmcp import FastMCP

from mongo_cache_mcp.config import CONFIG
from bson import ObjectId

from mongo_cache_mcp.storage import (
    get_mongo_client,
    get_database,
    get_collection,
    find_session_property,
    serialize_document,
    find_property,
    insert_property
    )

mcp = FastMCP(
    name="MongoCacheMCP",
    instructions=(
        "Provides cache lookup, cache upsert, TTL extension, and object retrieval "
        "for property documents stored in MongoDB."
    ),
)

def _get_collection():
    client = get_mongo_client()
    db = get_database(client)
    collection = get_collection(db)
    return client, collection

@mcp.tool()
def get_property(session_id: str, property_id: int | None = None, url: str | None = None) -> dict:
    """
    Find property by session_id and property_id or url.

    Returns:
    {
      "found": true,
      "mongo_id": "...",
      "document": {...}
    }
    """    
    client, collection = _get_collection()

    try:
        document = find_session_property(collection=collection, session_id=session_id, property_id=property_id, url=url)
        if document is None:
            return {
                "found": False,
                "session_id": session_id,
                "property_id": property_id,
                "url": url,
                "mongo_id": None,
                "mongo_path": None,
                "document": None,
            }

        serialized = serialize_document(document)

        mongo_id = serialized["_id"]

        return {
            "found": True,
            "session_id": session_id,
            "property_id": property_id,
            "url": url,
            "mongo_id": mongo_id,
            "path": f"{CONFIG.mongo_collection_name}/{mongo_id}",
            "document": serialized
        }
        
    finally:
        client.close()      

@mcp.tool()
def get_property_from_cache(property_id: int | None = None, url: str | None = None) -> dict:
    """
    Find cached property by property_id or url.

    Returns:
    {
      "found": true,
      "document": {...}
    }
    """   
    client, collection = _get_collection()

    try:
        document = find_property(collection, property_id=property_id, url=url)
        if document is None:
            return {
                "found": False,
                "property_id": property_id,
                "url": url,
                "document": None,
            }

        serialized = serialize_document(document)

        return {
            "found": True,
            "property_id": property_id,
            "url": url,
            "document": serialized
        }
        
    finally:
        client.close()

@mcp.tool()
def add_property(
    session_id: str, 
    payload: dict,
    status: str,
    reason: str,
    property_id: int | None = None,
    url: str | None = None,
) -> dict:
    """
    Create property in MongoDB and return mongo_id.

    Returns:
    {
      "mongo_id": "...",
      "path": "property_cache/<mongo_id>"
    }
    """

    client, collection = _get_collection()
    try:
        return insert_property(
            collection=collection,
            session_id=session_id,
            property_id=property_id,
            url=url,
            payload=payload,
            status=status,
            reason=reason
        )
    finally:
        client.close()

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=CONFIG.mcp_host,
        port=CONFIG.mcp_port,
    )