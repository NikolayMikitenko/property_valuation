import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

class AgentConfig(BaseModel):
    # mongo_store_mcp_url: str = Field(default=os.getenv("MONGO_STORE_MCP_URL", "http://127.0.0.1:8053/mcp"))
    mongo_store_mcp_url: str = Field(default=os.getenv("MONGO_STORE_MCP_URL"))
    # minio_proof_mcp_url: str = Field(default=os.getenv("SCREENSHOT_MCP_URL", "http://127.0.0.1:8050/mcp"))
    minio_proof_mcp_url: str = Field(default=os.getenv("SCREENSHOT_MCP_URL"))
    minio_bucket: str = Field(default=os.getenv("S3_BUCKET"))

    # research_a2a_url: str = Field(default=os.getenv("RESEARCH_A2A_URL", "http://127.0.0.1:9101"))
    research_a2a_url: str = Field(default=os.getenv("RESEARCH_A2A_URL"))
    # validator_a2a_url: str = Field(default=os.getenv("VALIDATOR_A2A_URL", "http://127.0.0.1:9102"))
    validator_a2a_url: str = Field(default=os.getenv("VALIDATOR_A2A_URL"))
    # proof_a2a_url: str = Field(default=os.getenv("PROOF_A2A_URL", "http://127.0.0.1:9103"))
    proof_a2a_url: str = Field(default=os.getenv("PROOF_A2A_URL"))

    # object_move_mcp_url: str = Field(default=os.getenv("OBJECT_MOVE_MCP_URL", "http://127.0.0.1:8000/mcp"))
    object_move_mcp_url: str = Field(default=os.getenv("OBJECT_MOVE_MCP_URL"))

    batch_size: int = Field(default=os.getenv("SUPERVISOR_STORE_BATCH_SIZE", 100))
    max_concurrency: int = Field(default=os.getenv("SUPERVISOR_SUBAGENT_MAX_CONCURENCY", 3))

CONFIG = AgentConfig()