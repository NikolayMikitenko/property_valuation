from __future__ import annotations

from pymongo import AsyncMongoClient

from valuation_store_api.config import CONFIG

client = AsyncMongoClient(CONFIG.mongo_uri)
db = client[CONFIG.mongo_db_name]

valuation_objects = db["valuation_objects"]
valuation_candidates = db["valuation_candidates"]