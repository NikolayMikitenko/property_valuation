import os

from pydantic import BaseModel, Field, field_validator


# Load .env from project root
from pathlib import Path
from dotenv import load_dotenv
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

class ScreenshotMCPConfig(BaseModel):
    minio_endpoint: str = Field(default=os.getenv("S3_ENDPOINT", "localhost:9000"))
    minio_access_key: str = Field(default=os.getenv("S3_ACCESS_KEY", "minioadmin"))
    minio_secret_key: str = Field(default=os.getenv("S3_SECRET_KEY", "minioadmin"))
    minio_bucket: str = Field(default=os.getenv("S3_BUCKET"))
    minio_prefix: str = Field(default=os.getenv("S3_PREFIX", "test/"))
    minio_region: str = Field(default=os.getenv("S3_REGION", "eu-central-1"))

    minio_secure: bool = Field(default=os.getenv("S3_SECURE", "false").lower() == "true")
    minio_verify_ssl: bool = Field(default=os.getenv("S3_VERIFY_SSL", "false").lower() == "true")
    
    ca_cert_path: str | None = Field(default=os.getenv("CA_CERT_PATH"))

    screenshot_max_attempts: int = Field(default=int(os.getenv("SCREENSHOT_MAX_ATTEMPTS", "3")))
    screenshot_timeout_ms: int = Field(default=int(os.getenv("SCREENSHOT_TIMEOUT_MS", "30000")))

    # mcp_host: str = Field(default=os.getenv("MCP_SCREENSHOT_HOST", "127.0.0.1"))
    mcp_host: str = Field(default=os.getenv("MCP_SCREENSHOT_HOST"))
    # mcp_port: int = Field(default=int(os.getenv("MCP_SCREENSHOT_PORT", "8050")))
    mcp_port: int = Field(default=int(os.getenv("MCP_SCREENSHOT_PORT")))

    @field_validator("minio_bucket", "minio_prefix", "mcp_host")
    @classmethod
    def validate_non_empty_str(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value must not be empty")
        return value

    @field_validator("screenshot_max_attempts")
    @classmethod
    def validate_attempts(cls, value: int) -> int:
        if value < 1:
            raise ValueError("SCREENSHOT_MAX_ATTEMPTS must be >= 1")
        return value
    
    @field_validator("screenshot_timeout_ms")
    @classmethod
    def validate_timeout(cls, value: int) -> int:
        if value < 1000:
            raise ValueError("SCREENSHOT_TIMEOUT_MS must be >= 1000")
        return value
    
    @field_validator("mcp_port")
    @classmethod
    def validate_port(cls, value: int) -> int:
        if value < 1 or value > 65535:
            raise ValueError("MCP_SCREENSHOT_PORT must be between 1 and 65535")
        return value

    @property
    def server_url(self) -> str:
        return f"http://{self.mcp_host}:{self.mcp_port}/mcp"

CONFIG = ScreenshotMCPConfig()