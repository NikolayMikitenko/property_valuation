import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

class DomRiaMCPConfig(BaseModel):

    mcp_host: str = Field(default=os.getenv("MCP_DOM_RIA_HOST"))
    mcp_port: int = Field(default=int(os.getenv("MCP_DOM_RIA_PORT")))

    @field_validator("mcp_host")
    @classmethod
    def validate_non_empty_str(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be empty")
        return value

    @field_validator("mcp_port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("MCP_DOM_RIA_PORT must be between 1 and 65535")
        return value

    @property
    def server_url(self) -> str:
        return f"http://{self.mcp_host}:{self.mcp_port}/mcp"

CONFIG = DomRiaMCPConfig()