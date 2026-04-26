import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class AgentConfig(BaseModel):
    # domria_mcp_url: str = Field(default=os.getenv("DOMRIA_MCP_URL", "http://127.0.0.1:8052/mcp"))
    domria_mcp_url: str = Field(default=os.getenv("DOMRIA_MCP_URL"))

    openai_api_base: str = Field(default=os.getenv("OPENAI_API_BASE"))
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY"))
    openai_lm_model: str = Field(default=os.getenv("OPENAI_LM_MODEL"))

    a2a_host: str = Field(default=os.getenv("RESEARCH_AGENT_A2A_HOST"))
    a2a_port: int = Field(default=int(os.getenv("RESEARCH_AGENT_A2A_PORT")))

CONFIG = AgentConfig()