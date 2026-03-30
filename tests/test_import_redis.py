import sys

import import_redis


def test_import_redis_delegates_to_backend(tmp_path, monkeypatch):
    class FakeRedis:
        def __init__(self) -> None:
            self.import_dir: str | None = None

        def import_datasource(self, import_dir: str) -> None:
            self.import_dir = import_dir

    fake = FakeRedis()
    monkeypatch.setattr(
        import_redis,
        "EDRedis",
        type("FakeEDRedis", (), {"create": staticmethod(lambda logger=None: fake)}),
    )
    fake_logger = type("Logger", (), {"info": lambda self, *args, **kwargs: None})()
    monkeypatch.setattr(import_redis, "configure_logging", lambda: None)
    monkeypatch.setattr(import_redis, "logger", fake_logger)
    monkeypatch.setattr(sys, "argv", ["import_redis.py", "--import-dir", str(tmp_path)])

    import_redis.main()
    assert fake.import_dir == str(tmp_path)
