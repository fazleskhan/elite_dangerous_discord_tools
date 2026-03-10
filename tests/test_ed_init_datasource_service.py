import pytest

from ed_route_services import EDInitDatasourceService


class _FakeDatasource:
    def init_datasource(self, import_dir: str = "./init") -> None:
        return None


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        EDInitDatasourceService(
            datasource=_FakeDatasource(),
            logging_utils=None,  # type: ignore[arg-type]
        )
