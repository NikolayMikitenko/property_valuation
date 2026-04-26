import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class AgentConfig(BaseModel):
    # screenshot_mcp_url: str = Field(default=os.getenv("SCREENSHOT_MCP_URL", "http://127.0.0.1:8050/mcp"))
    screenshot_mcp_url: str = Field(default=os.getenv("SCREENSHOT_MCP_URL"))

    a2a_host: str = Field(default=os.getenv("PROOF_AGENT_A2A_HOST"))
    a2a_port: int = Field(default=int(os.getenv("PROOF_AGENT_A2A_PORT")))

CONFIG = AgentConfig()