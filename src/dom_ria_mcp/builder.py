from __future__ import annotations

import requests
from urllib3.util.retry import Retry
from dom_ria_mcp.constants import (
    BASE_URL, AUTOCOMPLETE_URL, SEARCH_ENGINE_URL, REALTY_DATA_URL, 
    DEFAULT_HEADERS, OBJECTS, ROOMS, AREA, FLOORS, BUILDING_FLOORS, 
    FLOOR_FLAGS, REPAIR_CODES, PLANNING_CODES, WALL_TYPE_CODES, 
    WALL_TYPE_GROUP, HEATING_CODES, HEATING_GROUP, BUILD_YEAR_CODES, 
    BUILD_YEAR_GROUP, CURRENCY_GROUP, CURRENCY_CODES, 
    PRICE, PRICE_MODE_GROUP, PRICE_MODE_CODES
)
from requests.adapters import HTTPAdapter
from typing import Any, Optional
from dom_ria_mcp.schemas import SearchParams
from urllib.parse import urlencode
import re

ID_RE = re.compile(r"-(\d+)\.html$")

def create_session(additional_headers: dict = None) -> requests.Session:
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session = requests.Session()
    session.headers.update(DEFAULT_HEADERS)
    if additional_headers is not None:
        session.headers.update(additional_headers)
    session.mount("https://", HTTPAdapter(max_retries=retry))
    session.mount("http://", HTTPAdapter(max_retries=retry))
    return session

def get_json(url: str, params: Optional[dict[str, Any]] = None, additional_headers: dict = None) -> Any:
    with create_session(additional_headers=additional_headers) as session:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()

def get_text(url: str, params: Optional[dict[str, Any]] = None) -> tuple[str, requests.Response]:
    with create_session() as session:
        response = session.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.text, response

def flatten_autocomplete(payload: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for group_name, group_items in (payload.get("items") or {}).items():
        for item in group_items or []:
            p = item.get("payload") or {}
            items.append(
                {
                    "group": group_name,
                    "label": item.get("label"),
                    "output": item.get("output"),
                    "city_id": p.get("cityId") or p.get("id"),
                    "state_id": p.get("stateId"),
                    "name": p.get("name") or item.get("label"),
                    "city_name": p.get("cityName"),
                    "regionName": p.get("regionName"),
                    "state_name": p.get("stateName"),
                    # "entity_id": p.get("entityId"),
                    "center": item.get("center"), 
                    "raw": item,
                }
            )

    return items

def search_settlement_items(query: str, lang_id: int, only_city: int,) -> list[dict[str, Any]]:
    payload = get_json(
        AUTOCOMPLETE_URL,
        {
            "text": query,
            "lang_id": lang_id,
            "onlyCity": only_city,
        },
    )
    return flatten_autocomplete(payload)

def build_search_url(params: SearchParams) -> str:
    exclude_sold = True
    without_duplicates = True
    sort = "inspected_sort"
    obj = OBJECTS[params.object_key.value]
    query: dict[str, Any] = {
        "excludeSold": 1 if exclude_sold else 0,
        "category": obj["category"],
        "realty_type": obj["realty_type"],
        "operation": 1,
        "state_id": params.state_id,
        "price_cur": 1,
        "sort": sort,
        "firstIteraction": "false",
        "city_ids": params.city_id,
        "type": "list",
        "client": "searchV2",
        "limit": params.limit,
        "wo_dupl": 1 if without_duplicates else 0,
    }

    if params.building_id:
        query["bs_id"] =  params.building_id

    if params.street_id:
        query["s_id"] =  params.street_id

    if params.in_radius and params.in_radius > 0:
        query["in_radius"] = params.in_radius 

    if params.market_type and params.market_type.value == "secondary":
        query["secondary"] = 1
    if params.market_type and params.market_type.value == "newbuildings":
        query["newbuildings"] = 1

    if params.page > 1:
        query["page"] = params.page

    if params.date_from:
        query["date_from"] = params.date_from
    if params.date_to:
        query["date_to"] = params.date_to

    segments = build_ch_segments(params)
    if segments:
        query["ch"] = ",".join(segments)

    return f"{BASE_URL}/uk/search?{urlencode(query, doseq=True)}"

def build_ch_segments(params: SearchParams) -> list[str]:
    segments: list[str] = []

    if params.rooms_from is not None:
        segments.append(ROOMS["rooms_from"].format(value=params.rooms_from))
    if params.rooms_to is not None:
        segments.append(ROOMS["rooms_to"].format(value=params.rooms_to))

    if params.full_area_from is not None:
        segments.append(AREA["full_area_from"].format(value=params.full_area_from))
    if params.full_area_to is not None:
        segments.append(AREA["full_area_to"].format(value=params.full_area_to))
    if params.living_area_from is not None:
        segments.append(AREA["living_area_from"].format(value=params.living_area_from))
    if params.living_area_to is not None:
        segments.append(AREA["living_area_to"].format(value=params.living_area_to))
    if params.kitchen_area_from is not None:
        segments.append(AREA["kitchen_area_from"].format(value=params.kitchen_area_from))
    if params.kitchen_area_to is not None:
        segments.append(AREA["kitchen_area_to"].format(value=params.kitchen_area_to)) 

    if params.floors_from is not None:
        segments.append(FLOORS["floors_from"].format(value=params.floors_from))
    if params.floors_to is not None:
        segments.append(FLOORS["floors_to"].format(value=params.floors_to))    

    if params.building_floors_from is not None:
        segments.append(BUILDING_FLOORS["building_floors_from"].format(value=params.building_floors_from))
    if params.building_floors_to is not None:
        segments.append(BUILDING_FLOORS["building_floors_to"].format(value=params.building_floors_to))             

    if params.not_first_floor:
        segments.append(FLOOR_FLAGS["not_first_floor"])
    if params.not_last_floor:
        segments.append(FLOOR_FLAGS["not_last_floor"])

    if params.repair:
        segments.append(REPAIR_CODES[params.repair.value])

    for item in params.planning or []:
        segments.append(PLANNING_CODES[item.value])

    if params.wall_types:
        wall_values = [WALL_TYPE_CODES[item.value] for item in params.wall_types]
        segments.append(f"{WALL_TYPE_GROUP}_{':'.join(str(v) for v in wall_values)}:")

    if params.heating:
        heating_values = [HEATING_CODES[item.value] for item in params.heating]
        segments.append(f"{HEATING_GROUP}_{':'.join(str(v) for v in heating_values)}:")

    if params.build_years:
        year_values = [BUILD_YEAR_CODES[item.value] for item in params.build_years]
        segments.append(f"{BUILD_YEAR_GROUP}_{':'.join(str(v) for v in year_values)}:")

    if params.price_from is not None:
        segments.append(PRICE["price_from"].format(value=params.price_from))
    if params.price_to is not None:
        segments.append(PRICE["price_to"].format(value=params.price_to))    

    if params.currency:
        segments.append(f"{CURRENCY_GROUP}_{CURRENCY_CODES[params.currency.value]}:")
    if params.price_mode:
        segments.append(f"{PRICE_MODE_GROUP}_{PRICE_MODE_CODES[params.price_mode.value]}:")

    # for raw in params.raw_ch_segments or []:
    #     if raw:
    #         segments.append(raw)

    return segments

def build_search_engine_params(
    params: SearchParams,
    *,
    # page: int = 0,
    # limit: int = 100,
    exclude_sold: bool = True,
    without_duplicates: bool = True,
    sort: str = "inspected_sort",
    add_more_realty: bool = False,
) -> dict[str, Any]:
    obj = OBJECTS[params.object_key.value]

    query: dict[str, Any] = {
        "addMoreRealty": "true" if add_more_realty else "false",
        "excludeSold": 1 if exclude_sold else 0,
        "category": obj["category"],
        "realty_type": obj["realty_type"],
        "operation": 1,
        "operation_type": 1,
        "state_id": params.state_id,
        "city_id": params.city_id,
        # "city_id": 0,  # frontend often sends exact filter through city_ids
        # "city_ids": city_ids,
        "city_ids": params.city_id,
        "in_radius": params.in_radius if params.in_radius else 0,
        "with_newbuilds": 0,
        "price_cur": 1,
        "wo_dupl": 1 if without_duplicates else 0,
        "complex_inspected": 0,
        "sort": sort,
        # "period": 0,
        "notFirstFloor": 1 if params.not_first_floor else 0,
        "notLastFloor": 1 if params.not_last_floor else 0,
        "with_map": 0,
        "photos_count_from": 0,
        "with_video_only": 0,
        "firstIteraction": "false",
        "fromAmp": 0,
        "type": "list",
        "client": "searchV2",
        "limit": params.limit,
        "page": params.page,
        "mobileStatus": 0,
    }

    if params.building_id:
        query["bs_id"] =  params.building_id

    if params.street_id:
        query["s_id"] =  params.street_id

    if params.market_type:
        if params.market_type.value == "newbuildings":
            query["newbuildings"] = 1

    if params.date_from is None and params.date_to is None:
        query["period"] = 0

    if params.date_from:
        query["date_from"] = params.date_from
    if params.date_to:
        query["date_to"] = params.date_to

    segments = build_ch_segments_for_search_engine(params)
    if segments:
        query["ch"] = ",".join(segments)

    return query

def build_ch_segments_for_search_engine(params: SearchParams) -> list[str]:
    segments: list[str] = []

    if params.rooms_from is not None:
        segments.append(ROOMS["rooms_from"].format(value=params.rooms_from))
    if params.rooms_to is not None:
        segments.append(ROOMS["rooms_to"].format(value=params.rooms_to))

    if params.full_area_from is not None:
        segments.append(AREA["full_area_from"].format(value=params.full_area_from))
    if params.full_area_to is not None:
        segments.append(AREA["full_area_to"].format(value=params.full_area_to))

    if params.living_area_from is not None:
        segments.append(AREA["living_area_from"].format(value=params.living_area_from))
    if params.living_area_to is not None:
        segments.append(AREA["living_area_to"].format(value=params.living_area_to))

    if params.kitchen_area_from is not None:
        segments.append(AREA["kitchen_area_from"].format(value=params.kitchen_area_from))
    if params.kitchen_area_to is not None:
        segments.append(AREA["kitchen_area_to"].format(value=params.kitchen_area_to))

    if params.floors_from is not None:
        segments.append(FLOORS["floors_from"].format(value=params.floors_from))
    if params.floors_to is not None:
        segments.append(FLOORS["floors_to"].format(value=params.floors_to))

    if params.building_floors_from is not None:
        segments.append(BUILDING_FLOORS["building_floors_from"].format(value=params.building_floors_from))
    if params.building_floors_to is not None:
        segments.append(BUILDING_FLOORS["building_floors_to"].format(value=params.building_floors_to))

    if params.repair:
        segments.append(REPAIR_CODES[params.repair.value])

    for item in params.planning or []:
        segments.append(PLANNING_CODES[item.value])

    if params.wall_types:
        wall_values = [WALL_TYPE_CODES[item.value] for item in params.wall_types]
        segments.append(f"{WALL_TYPE_GROUP}_{':'.join(str(v) for v in wall_values)}:")

    if params.heating:
        heating_values = [HEATING_CODES[item.value] for item in params.heating]
        segments.append(f"{HEATING_GROUP}_{':'.join(str(v) for v in heating_values)}:")

    if params.build_years:
        year_values = [BUILD_YEAR_CODES[item.value] for item in params.build_years]
        segments.append(f"{BUILD_YEAR_GROUP}_{':'.join(str(v) for v in year_values)}:")

    if params.price_from is not None:
        segments.append(PRICE["price_from"].format(value=params.price_from))
    if params.price_to is not None:
        segments.append(PRICE["price_to"].format(value=params.price_to))    

    if params.currency:
        segments.append(f"{CURRENCY_GROUP}_{CURRENCY_CODES[params.currency.value]}:")
    if params.price_mode:
        segments.append(f"{PRICE_MODE_GROUP}_{PRICE_MODE_CODES[params.price_mode.value]}:")        

    return segments

def get_search_objects(params, search_url) -> list[dict[str, Any]]:
    payload = get_json(
        SEARCH_ENGINE_URL,
        params,
        {"Referer": search_url}
    )
    return {"search_url":search_url, "count":payload.get("count"), "items_ids":payload.get("items")}

def get_object(item_id, search_url) -> list[dict[str, Any]]:
    payload = get_json(
        f"{REALTY_DATA_URL}/{item_id}",
        {"lang_id":4,"key":""},
        {"Referer": search_url}
    )
    payload['item_id']=item_id
    payload['url']=f"{BASE_URL}/uk/{payload.get("beautiful_url")}"
    return payload