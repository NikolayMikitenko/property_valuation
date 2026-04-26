from fastmcp import FastMCP
# from typing import Any

from dom_ria_mcp.config import CONFIG
from dom_ria_mcp.builder import (
    search_settlement_items,
    get_search_objects,
    get_object,
    build_search_url,
    build_search_engine_params,
)

from dom_ria_mcp.schemas import (
    BuildYear,
    Currency,
    HeatingType,
    MarketType,
    ObjectKey,
    PlanningOption,
    PriceMode,
    RepairType,
    SearchParams,
    WallType,
)

mcp = FastMCP(
    name="DomRiaMCP",
    instructions=(
        "Provide detail information about property from DomRia web site"
    ),
)

@mcp.tool()
def get_address_ids(address: str, lang_id: int = 4): # -> list[dict[str, any]]:
    """Шукає населений пункт через autocomplete DOM.RIA і повертає city_id/state_id."""
    only_city = 0
    items = search_settlement_items(address, lang_id, only_city)
    return items

@mcp.tool()
def search_objects(
    object_key: ObjectKey,
    building_id: str | None = None,
    street_id: int | None = None,
    city_id: int | None = None,
    state_id: int | None = None,
    in_radius: int | None = None,
    market_type: MarketType | None = None,
    rooms_from: int | None = None,
    rooms_to: int | None = None,
    full_area_from: int | None = None,
    full_area_to: int | None = None,
    living_area_from: int | None = None,
    living_area_to: int | None = None,
    kitchen_area_from: int | None = None,
    kitchen_area_to: int | None = None,
    floors_from: int | None = None,
    floors_to: int | None = None,
    building_floors_from: int | None = None,
    building_floors_to: int | None = None,
    not_first_floor: bool | None = None,
    not_last_floor: bool | None = None,
    repair: RepairType | None = None,
    planning: list[PlanningOption] | None = None,
    wall_types: list[WallType] | None = None,
    heating: list[HeatingType] | None = None,
    build_years: list[BuildYear] | None = None,
    price_from: int | None = None,
    price_to: int | None = None,
    currency: Currency | None = None,
    price_mode: PriceMode | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    page: int = 1,
    limit: int = 100,
): 
    params = SearchParams(
        object_key=object_key,
        building_id=building_id,
        street_id=street_id,
        city_id=city_id,
        state_id=state_id,
        in_radius=in_radius,
        market_type=market_type,
        rooms_from=rooms_from,
        rooms_to=rooms_to,
        full_area_from=full_area_from,
        full_area_to=full_area_to,
        living_area_from=living_area_from,
        living_area_to=living_area_to,
        kitchen_area_from=kitchen_area_from,
        kitchen_area_to=kitchen_area_to,
        floors_from=floors_from,
        floors_to=floors_to,
        building_floors_from=building_floors_from,
        building_floors_to=building_floors_to,
        not_first_floor=not_first_floor,
        not_last_floor=not_last_floor,
        repair=repair,
        planning=planning,
        wall_types=wall_types,
        heating=heating,
        build_years=build_years,
        price_from=price_from,
        price_to=price_to,
        currency=currency,
        price_mode=price_mode,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )
    """Формує URL строку для пошуку оголошень на DOM.RIA про нерухоме майно та повертає масив ідентифікаторів обєктів."""
    search_url = build_search_url(params)
    api_params = build_search_engine_params(params)
    return get_search_objects(api_params, search_url)

@mcp.tool()
def get_object_by_id(item_id: int, search_url: str):
    """Повертає детальну інформацію про об'єкт нерухомості із сайту оголошень DOM.RIA за його ID"""
    if search_url is None:
        search_url = ""
    return get_object(item_id, search_url)

if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=CONFIG.mcp_host,
        port=CONFIG.mcp_port,
    )

# async def amain():
#     await mcp.run_async(
#         transport="streamable-http",
#         host=CONFIG.mcp_host,
#         port=CONFIG.mcp_port,
#     )

# def main():
#     mcp.run(
#         transport="http",
#         host=CONFIG.mcp_host,
#         port=CONFIG.mcp_port,
#         )

# if __name__ == "__main__":
#     asyncio.run(amain())