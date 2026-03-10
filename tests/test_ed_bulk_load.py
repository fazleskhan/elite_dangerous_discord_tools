import pytest
from ed_bulk_load_algo import EDBulkLoadAlgo


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        EDBulkLoadAlgo(
            fetch_system_info_fn=lambda _name: None,
            fetch_neighbors_fn=lambda _system_info: None,
            logging_utils=None,
        )
