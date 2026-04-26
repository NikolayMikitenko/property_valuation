import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

class MongoCacheMCPConfig(BaseModel):
    # mongo_uri: str = Field(default=os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    mongo_uri: str = Field(default=os.getenv("MONGO_URI"))
    mongo_db_name: str = Field(default=os.getenv("MONGO_DB_NAME"))
    mongo_collection_name: str = Field(default=os.getenv("MONGO_COLLECTION_NAME"))

    cache_ttl_seconds: int = Field(default=int(os.getenv("CACHE_TTL_SECONDS", "604800")))  # 7 days

    # mcp_host: str = Field(default=os.getenv("MCP_MONGO_CACHE_HOST", "127.0.0.1"))
    mcp_host: str = Field(default=os.getenv("MCP_MONGO_CACHE_HOST"))
    # mcp_port: int = Field(default=int(os.getenv("MCP_MONGO_CACHE_PORT", "8051")))
    mcp_port: int = Field(default=int(os.getenv("MCP_MONGO_CACHE_PORT")))

    @field_validator("mongo_uri", "mongo_db_name", "mongo_collection_name", "mcp_host")
    @classmethod
    def validate_non_empty_str(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be empty")
        return value

    @field_validator("cache_ttl_seconds")
    @classmethod
    def validate_cache_ttl_seconds(cls, value: int) -> int:
        if value < 60:
            raise ValueError("CACHE_TTL_SECONDS must be >= 60")
        return value

    @field_validator("mcp_port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("MCP_MONGO_CACHE_PORT must be between 1 and 65535")
        return value

    @property
    def server_url(self) -> str:
        return f"http://{self.mcp_host}:{self.mcp_port}/mcp"


CONFIG = MongoCacheMCPConfig()