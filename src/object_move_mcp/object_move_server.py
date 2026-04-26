from __future__ import annotations

from typing import Any
from mcp.server.fastmcp import FastMCP

from object_move_mcp.minio_move_utils import move_minio_object_from_temporary_to_permanent_store

from object_move_mcp.config import CONFIG

mcp = FastMCP(
    "object_move",
    host=CONFIG.mcp_host,
    port=CONFIG.mcp_port,
    # path=CONFIG.mcp_path,
)

@mcp.tool()
def move_object_from_temporary_to_permanent_store(
    source_path: str,
    target_bucket: str,
    ttl_days: int = 30,
) -> dict[str, Any]:
    return move_minio_object_from_temporary_to_permanent_store(
        source_path=source_path,
        target_bucket=target_bucket,
        ttl_days=ttl_days,
    )

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
    )