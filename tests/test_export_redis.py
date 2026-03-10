import sys

import export_redis
import pytest


def main() -> None: ...


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        export_redis.ExportRedis(
            route_service=None,
            cache=None,
            logging_utils=None,  # type: ignore[arg-type]
        )


def test_export_redis_delegates_to_backend(tmp_path, monkeypatch):
    class FakeRedisDB:
        def __init__(self):
            self.export_dir = None

        def export_datasource(self, export_dir: str):
            self.export_dir = export_dir

    class FakeEDRedis:
        @staticmethod
        def create(
            datasource_name: str = "ed_route", *, logging_utils=None
        ):
            return fake_db

    fake_db = FakeRedisDB()
    monkeypatch.setattr(export_redis, "EDRedis", FakeEDRedis)
    monkeypatch.setattr(export_redis.EDLoggingUtils, "create", lambda: object())
    export_dir = tmp_path / "ed_redis-export"
    monkeypatch.setattr(
        sys, "argv", ["export_redis.py", "--export-dir", str(export_dir)]
    )

    export_redis.main()

    assert fake_db.export_dir == str(export_dir)


if __name__ == "__main__":
    main()
