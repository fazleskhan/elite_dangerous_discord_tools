import sys

import import_redis


def main() -> None: ...


def test_import_redis_delegates_to_backend(tmp_path, monkeypatch):
    class FakeRedisDB:
        def __init__(self):
            self.import_dir = None

        def import_datasource(self, import_dir: str):
            self.import_dir = import_dir

    fake_db = FakeRedisDB()
    monkeypatch.setattr(import_redis, "EDRedis", lambda database_name: fake_db)

    import_dir = tmp_path / "ed_tinydb-export"
    import_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        sys, "argv", ["import_redis.py", "--import-dir", str(import_dir)]
    )
    import_redis.main()

    assert fake_db.import_dir == str(import_dir)


if __name__ == "__main__":
    main()
