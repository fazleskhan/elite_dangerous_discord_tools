"""IoC helpers for datasource/cache/route service composition."""

import os
from typing import Any, Callable, Protocol

from dotenv import load_dotenv

import ed_bfs
import ed_route
import edgis_cache

SystemInfo = dict[str, Any]
TravelFn = Callable[..., list[str] | None]


def main() -> None: ...


class DBProtocol(Protocol):
    def init_datasource(self, import_dir: str = "./init") -> None: ...
    def get_all_systems(self) -> list[SystemInfo]: ...


class EDDatasourceFactory:
    """Factory for selecting concrete datasource implementations."""

    def __init__(self, logging_utils: Any) -> None:
        self._logging_utils = logging_utils

    @staticmethod
    def create(logging_utils: Any) -> "EDDatasourceFactory":
        return EDDatasourceFactory(logging_utils)

    @staticmethod
    def create_datasource(
        logging_utils: Any,
        datasource_name: str | None,
        datasource_type: str | None,
    ) -> DBProtocol:
        load_dotenv()
        resolved_type = resolve_datasource_type(datasource_type)
        if resolved_type == "tinydb":
            from ed_tinydb import EDTinyDB

            return EDTinyDB.create(datasource_name=datasource_name)

        from ed_redis import EDRedis

        return EDRedis.create(datasource_name=datasource_name)


def resolve_datasource_type(datasource_type: str | None = None) -> str:
    # Explicit arg wins, then env, then tinydb default.
    resolved = (
        (datasource_type or os.getenv("DATASOURCE_TYPE") or "tinydb").strip().lower()
    )
    if resolved not in {"tinydb", "redis"}:
        raise ValueError(
            "Invalid DATASOURCE_TYPE value. Supported values are 'tinydb' and 'redis'."
        )
    return resolved


def create_datasource(
    datasource_name: str | None = None, datasource_type: str | None = None
) -> Any:
    return EDDatasourceFactory.create_datasource(
        logging_utils=None,
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )


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
