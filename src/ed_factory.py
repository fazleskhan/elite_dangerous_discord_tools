"""IoC helpers for datasource/cache/route service composition."""

import importlib
import os
from typing import TYPE_CHECKING, Any, Callable

from dotenv import load_dotenv

import ed_bfs
import edgis_cache
from ed_constants import (
    datasource_type_env,
    redis_name,
    tinydb_name,
)
from ed_protocols import DatasourceProtocol

if TYPE_CHECKING:
    from ed_route import EDRouteService

TravelFn = Callable[..., list[str] | None]


class _LazyModuleProxy:
    """Resolve modules on first attribute access to avoid import cycles."""

    def __init__(self, module_name: str) -> None:
        self._module_name = module_name

    def __getattr__(self, item: str) -> Any:
        module = importlib.import_module(self._module_name)
        return getattr(module, item)


ed_route = _LazyModuleProxy("ed_route")


def main() -> None: ...


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
    ) -> DatasourceProtocol:
        load_dotenv()
        resolved_type = resolve_datasource_type(datasource_type)
        if resolved_type == tinydb_name:
            from ed_tinydb import EDTinyDB

            return EDTinyDB.create(datasource_name=datasource_name)

        from ed_redis import EDRedis

        return EDRedis.create(datasource_name=datasource_name)


def resolve_datasource_type(datasource_type: str | None = None) -> str:
    # Explicit arg wins, then env, then tinydb default.
    resolved = (
        (
            datasource_type
            or os.getenv(datasource_type_env)
            or tinydb_name
        )
        .strip()
        .lower()
    )
    if resolved not in {tinydb_name, redis_name}:
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
) -> "EDRouteService":
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
