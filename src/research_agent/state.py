from __future__ import annotations
from research_agent.schema import AssetKind, PropertyType, PropertySubtype

from typing import TypedDict

class InputState(TypedDict):
    user_query: str

class AgentState(TypedDict, total=False):
    user_query: str

    asset_kind: AssetKind
    property_type: PropertyType
    property_subtype: PropertySubtype

    address: str | None

    building_id: str | None
    city_id: int | None
    state_id: int | None
    street_id: int | None
    longitude: str | None
    latitude: str | None

    search_level: str | None

    search_url: str | None
    candidates_ids: list[int] | None
    all_candidates_ids: list[int] | None
    source: None
    status: str | None

class OutputState(TypedDict):
    # asset_kind: AssetKind | None
    # property_type: PropertyType | None
    # property_subtype: PropertySubtype | None

    # building_id: str | None
    # street_id: int | None
    # city_id: int | None
    # state_id: int | None
    # longitude: str | None
    # latitude: str | None

    search_url: str | None
    candidates_ids: list[int] | None
    source: None