import pytest

from ed_route import EDRouteService


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        EDRouteService(
            datasource=None,
            cache=None,
            bfs=None,  # type: ignore[arg-type]
            logging_utils=None,  # type: ignore[arg-type]
            init_datasource_service=None,  # type: ignore[arg-type]
            get_system_info_service=None,  # type: ignore[arg-type]
            get_all_system_names_service=None,  # type: ignore[arg-type]
            bulk_load_cache_service=None,  # type: ignore[arg-type]
            path_service=None,  # type: ignore[arg-type]
            calc_systems_distance_service=None,  # type: ignore[arg-type]
        )
