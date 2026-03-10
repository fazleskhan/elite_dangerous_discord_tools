import sys

import export_redis


def test_export_redis_delegates_to_backend(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    class FakeRedis:
        def __init__(self) -> None:
            self.export_dir = None

        def export_datasource(self, export_dir: str) -> None:
            self.export_dir = export_dir

    fake = FakeRedis()
    monkeypatch.setattr(export_redis, "EDRedis", type("FakeEDRedis", (), {"create": staticmethod(lambda logging_utils=None: fake)}))
    monkeypatch.setattr(export_redis.EDLoggingUtils, "create", lambda: object())
    monkeypatch.setattr(sys, "argv", ["export_redis.py", "--export-dir", str(tmp_path)])

    export_redis.main()
    assert fake.export_dir == str(tmp_path)
