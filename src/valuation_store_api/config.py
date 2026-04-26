from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class MongoStoreMCPConfig(BaseModel):
    # mongo_uri: str = Field(default=os.getenv("MONGO_URI", "mongodb://localhost:27017"))
    mongo_uri: str = Field(default=os.getenv("MONGO_URI"))
    mongo_db_name: str = Field(default=os.getenv("MONGO_DB_NAME"))
#     mongo_collection_name: str = Field(default=os.getenv("MONGO_COLLECTION_NAME", "property_cache"))

#     cache_ttl_seconds: int = Field(default=int(os.getenv("CACHE_TTL_SECONDS", "604800")))  # 7 days

CONFIG = MongoStoreMCPConfig()