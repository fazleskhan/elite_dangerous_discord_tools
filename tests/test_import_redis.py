import sys

import import_redis


def test_import_redis_delegates_to_backend(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    class FakeRedis:
        def __init__(self) -> None:
            self.import_dir = None

        def import_datasource(self, import_dir: str) -> None:
            self.import_dir = import_dir

    fake = FakeRedis()
    monkeypatch.setattr(import_redis, "EDRedis", type("FakeEDRedis", (), {"create": staticmethod(lambda logging_utils=None: fake)}))
    monkeypatch.setattr(import_redis.EDLoggingUtils, "create", lambda: object())
    monkeypatch.setattr(sys, "argv", ["import_redis.py", "--import-dir", str(tmp_path)])

    import_redis.main()
    assert fake.import_dir == str(tmp_path)
