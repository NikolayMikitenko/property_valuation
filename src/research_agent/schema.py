from __future__ import annotations

from typing import Literal
from pydantic import BaseModel

OBJECTS = {
    "flat": ["flat"],
    "room": ["room"],
    "house": ["private_house", "duplex", "townhouse", "part_of_house", "all_house_types"],
    "commercial": ["office", "commerce", "special", "all_commercial_types"]
}

SEARCH_LEVEL_NEXT: dict[str, str] = {
    "building": "street",
    "street": "city",
    "city": "city_5",
    "city_5": "city_10",
    "city_10": "city_15",
    "city_15": "city_20",
    "city_20": "city_30",
}

AssetKind = Literal["real_estate", "equipment"]
PropertyType = Literal["flat", "room", "house", "commercial"]
PropertySubtype = Literal[
    "flat",
    "room",
    "private_house",
    "duplex",
    "townhouse",
    "part_of_house",
    "all_house_types",
    "office",
    "commerce",
    "special",
    "all_commercial_types",
]
AddressType = Literal["building", "street", "city"]

class DetectAssetKindResult(BaseModel):
    asset_kind: AssetKind

class DetectPropertyTypeResult(BaseModel):
    property_type: PropertyType

class DetectPropertySubtypeResult(BaseModel):
    property_subtype: PropertySubtype

class SelectDomRiaObjectLocationResult(BaseModel):
    type: AddressType
    building_id: str | None
    street_id: str | None
    city_id: int
    state_id: int
    longitude: float
    latitude: float

# class ObjectLocationResult(BaseModel):
#     building_id: str
#     city_id: int
#     state_id: int
#     street_id: int