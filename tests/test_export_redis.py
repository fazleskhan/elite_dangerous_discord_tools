import sys

import export_redis


def main() -> None: ...


def test_export_redis_delegates_to_backend(tmp_path, monkeypatch):
    class FakeRedisDB:
        def __init__(self):
            self.export_dir = None

        def export_datasource(self, export_dir: str):
            self.export_dir = export_dir

    class FakeEDRedis:
        @staticmethod
        def create(datasource_name: str = "ed_route"):
            return fake_db

    fake_db = FakeRedisDB()
    monkeypatch.setattr(export_redis, "EDRedis", FakeEDRedis)
    export_dir = tmp_path / "ed_redis-export"
    monkeypatch.setattr(
        sys, "argv", ["export_redis.py", "--export-dir", str(export_dir)]
    )

    export_redis.main()

    assert fake_db.export_dir == str(export_dir)


if __name__ == "__main__":
    main()
