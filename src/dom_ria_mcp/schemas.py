from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

class ModelBase(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

class ObjectKey(str, Enum):
    flat = "flat"
    room = "room"
    private_house = "private_house"
    duplex = "duplex"
    townhouse = "townhouse"
    part_of_house = "part_of_house"
    all_house_types = "all_house_types"
    office = "office"
    commerce = "commerce"
    special = "special"
    all_commercial_types = "all_commercial_types"

class MarketType(str, Enum):
    secondary = "secondary"
    newbuildings = "newbuildings"

class RepairType(str, Enum):
    with_repair = "with_repair"
    without_repair = "without_repair"

class PlanningOption(str, Enum):
    kitchen_studio = "kitchen_studio"
    multi_level = "multi_level"
    with_attic = "with_attic"
    penthouse = "penthouse"
    terrace = "terrace"
    without_furniture = "without_furniture"

class WallType(str, Enum):
    brick = "brick"
    frame = "frame"
    panel = "panel"
    block = "block"
    monolith = "monolith"
    stone = "stone"
    reinforced_concrete = "reinforced_concrete"
    wood = "wood"

class HeatingType(str, Enum):
    central = "central"
    individual = "individual"
    combined = "combined"
    absent = "absent"

class BuildYear(str, Enum):
    handover_2028 = "handover_2028"
    handover_2027 = "handover_2027"
    handover_2026 = "handover_2026"
    y2025 = "2025"
    y2024 = "2024"
    y2023 = "2023"
    y2022 = "2022"
    y2021 = "2021"
    y2020 = "2020"
    y2019 = "2019"
    y2018 = "2018"
    y2017 = "2017"
    y2016 = "2016"
    y2011_2015 = "2011_2015"
    y2001_2010 = "2001_2010"
    y1990_2000 = "1990_2000"
    y1980_1989 = "1980_1989"
    y1970_1979 = "1970_1979"
    y1917_1969 = "1917_1969"
    before_1917 = "before_1917"

class Currency(str, Enum):
    usd = "usd"
    uah = "uah"
    eur = "eur"

class PriceMode(str, Enum):
    per_object = "per_object"
    per_sqm = "per_sqm"

class SearchParams(ModelBase):
    object_key: ObjectKey = Field(description="Тип об'єкта з OBJECTS")

    building_id: Optional[str] = Field(default=None, description="DOM.RIA building_id")
    street_id: Optional[int] = Field(default=None, description="DOM.RIA street_id")
    city_id: Optional[int] = Field(default=None, description="DOM.RIA city_id")
    state_id: Optional[int] = Field(default=None, description="DOM.RIA state_id")

    in_radius: Optional[int] = Field(default=None, description="Search radius in kilometers")

    market_type: Optional[MarketType] = Field(default=None, description="secondary або newbuildings")

    rooms_from: Optional[int] = None
    rooms_to: Optional[int] = None

    full_area_from: Optional[int] = None
    full_area_to: Optional[int] = None
    living_area_from: Optional[int] = None
    living_area_to: Optional[int] = None
    kitchen_area_from: Optional[int] = None
    kitchen_area_to: Optional[int] = None

    floors_from: Optional[int] = None
    floors_to: Optional[int] = None
    building_floors_from: Optional[int] = None
    building_floors_to: Optional[int] = None

    not_first_floor: Optional[bool] = None
    not_last_floor: Optional[bool] = None

    repair: Optional[RepairType] = None
    planning: Optional[list[PlanningOption]] = None
    wall_types: Optional[list[WallType]] = None
    heating: Optional[list[HeatingType]] = None
    build_years: Optional[list[BuildYear]] = None

    price_from: Optional[int] = None
    price_to: Optional[int] = None
    currency: Optional[Currency] = Field(default=Currency.usd)
    price_mode: Optional[PriceMode] = Field(default=PriceMode.per_object)

    date_from: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    date_to: Optional[str] = Field(default=None, description="YYYY-MM-DD")

    page: int
    limit: int