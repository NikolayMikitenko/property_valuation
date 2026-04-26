from __future__ import annotations

BASE_URL = "https://dom.ria.com"
AUTOCOMPLETE_URL = f"{BASE_URL}/node/api/autocompleteV3"
SEARCH_ENGINE_URL = f"{BASE_URL}/node/searchEngine/v2/"
REALTY_DATA_URL = f"{BASE_URL}/realty/data/"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "uk,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7",
}

WALL_TYPE_GROUP = 118
WALL_TYPE_CODES = {
    "brick": 108,
    "frame": 1782,
    "panel": 110,
    "block": 111,
    "monolith": 113,
    "stone": 114,
    "reinforced_concrete": 1621,
    "wood": 1962,
}

HEATING_GROUP = 1650
HEATING_CODES = {
    "central": 1648,
    "individual": 1649,
    "combined": 1881,
    "absent": 1653,
}

BUILD_YEAR_GROUP = 443
BUILD_YEAR_CODES = {
    "handover_2028": 2100,
    "handover_2027": 1995,
    "handover_2026": 1876,
    "2025": 1875,
    "2024": 1874,
    "2023": 1873,
    "2022": 1752,
    "2021": 1751,
    "2020": 1471,
    "2019": 1470,
    "2018": 1469,
    "2017": 1468,
    "2016": 1789,
    "2011_2015": 1784,
    "2001_2010": 1783,
    "1990_2000": 435,
    "1980_1989": 436,
    "1970_1979": 437,
    "1917_1969": 1791,
    "before_1917": 441,
}

PLANNING_CODES = {
    "kitchen-studio": "1501_1501",
    "multi-level": "1502_1502",
    "with_attic": "1503_1503",
    "penthouse": "1504_1504",
    "terrace": "1638_1638",
    "without_furniture": "1646_1646",
}

REPAIR_CODES = {
    "with_repair": "1479_1479",
    "without_repair": "791_791",
}

FLOOR_FLAGS = {
    "not_first_floor": "1644_1644",
    "not_last_floor": "1645_1645",
}

BUILDING_FLOORS = {
    "building_floors_from": "228_f_{value}",
    "building_floors_to": "228_t_{value}"
}

FLOORS = {
    "floors_from": "227_f_{value}",
    "floors_to": "227_t_{value}"
}

AREA = {
    "full_area_from": "214_f_{value}",
    "full_area_to": "214_t_{value}",
    "living_area_from": "216_f_{value}",
    "living_area_to": "216_t_{value}",
    "kitchen_area_from": "218_f_{value}",
    "kitchen_area_to": "218_t_{value}",
}

ROOMS = {
    "rooms_from": "209_f_{value}",
    "rooms_to": "209_t_{value}",
}

PRICE = {
    "price_from": "234_f_{value}",
    "price_to": "234_t_{value}",
}

CURRENCY_GROUP = 242
CURRENCY_CODES = {
    "usd": 239,
    "uah": 240,
    "eur": 241,
}

PRICE_MODE_GROUP = 247
PRICE_MODE_CODES = {
    "per_object": 252,
    "per_sqm": 253,
}

OBJECTS = {
    "flat": {"type": "flat", "category": 1, "realty_type": 2},
    "room": {"type": "room", "category": 40, "realty_type": 3},

    "private_house": {"type": "house", "category": 4, "realty_type": 5},
    "duplex": {"type": "house", "category": 4, "realty_type": 8},
    "townhouse": {"type": "house", "category": 4, "realty_type": 9},
    "part_of_house": {"type": "house", "category": 4, "realty_type": 6},
    "all_house_types": {"type": "house", "category": 4, "realty_type": 0},

    "office": {"type": "commercial", "category": 13, "realty_type": 11},
    "commerce": {"type": "commercial", "category": 13, "realty_type": 21},
    "special": {"type": "commercial", "category": 13, "realty_type": 18},
    "all_commercial_types": {"type": "commercial", "category": 13, "realty_type": 0},
}