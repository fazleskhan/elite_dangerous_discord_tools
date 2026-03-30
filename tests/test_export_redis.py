import sys

import export_redis


def test_export_redis_delegates_to_backend(tmp_path, monkeypatch):
    class FakeRedis:
        def __init__(self) -> None:
            self.export_dir: str | None = None

        def export_datasource(self, export_dir: str) -> None:
            self.export_dir = export_dir

    fake = FakeRedis()
    monkeypatch.setattr(
        export_redis,
        "EDRedis",
        type("FakeEDRedis", (), {"create": staticmethod(lambda logger=None: fake)}),
    )
    fake_logger = type("Logger", (), {"info": lambda self, *args, **kwargs: None})()
    monkeypatch.setattr(export_redis, "configure_logging", lambda: None)
    monkeypatch.setattr(export_redis, "logger", fake_logger)
    monkeypatch.setattr(sys, "argv", ["export_redis.py", "--export-dir", str(tmp_path)])

    export_redis.main()
    assert fake.export_dir == str(tmp_path)
