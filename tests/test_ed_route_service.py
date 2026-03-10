import pytest

from ed_route import EDRouteService


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        EDRouteService(
            db_path="test.db",
            database=None,
            cache=None,
            travel_fn=None,
            script_file=__file__,
            logging_utils=None,  # type: ignore[arg-type]
        )
