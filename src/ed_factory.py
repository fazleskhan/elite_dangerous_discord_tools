"""IoC helpers for datasource/cache/route service composition."""

import os
from typing import Any, Callable

from dotenv import load_dotenv

import ed_bfs
import ed_route
import edgis_cache

SystemInfo = dict[str, Any]
TravelFn = Callable[..., list[str] | None]


def main() -> None: ...


def resolve_datasource_type(datasource_type: str | None = None) -> str:
    resolved = (
        datasource_type
        or os.getenv("DATASOURCE_TYPE")
        or "tinydb"
    ).strip().lower()
    if resolved not in {"tinydb", "redis"}:
        raise ValueError(
            "Invalid DATASOURCE_TYPE value. Supported values are 'tinydb' and 'redis'."
        )
    return resolved


def create_datasource(
    datasource_name: str | None = None, datasource_type: str | None = None
) -> Any:
    load_dotenv()
    resolved_type = resolve_datasource_type(datasource_type)
    if resolved_type == "tinydb":
        from ed_tinydb import EDTinyDB

        return EDTinyDB.create(datasource_name=datasource_name)

    from ed_redis import EDRedis

    return EDRedis.create(datasource_name=datasource_name)


def create_route_service(
    datasource_name: str | None = None,
    datasource_type: str | None = None,
    travel_fn: TravelFn = ed_bfs.travel,
) -> ed_route.EDRouteService:
    datasource_obj = create_datasource(
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )
    cache_obj = edgis_cache.EDGisCache.create(datasource_obj)
    return ed_route.EDRouteService.create(
        datasource=datasource_obj,
        cache=cache_obj,
        travel_fn=travel_fn,
    )


if __name__ == "__main__":
    main()
