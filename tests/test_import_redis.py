import json
import sys

import import_redis
import pytest


def main() -> None: ...


def test_import_redis_loads_json_files_and_inserts(tmp_path, monkeypatch):
    class FakeRedisDB:
        def __init__(self):
            self.inserted = []

        def insert_system(self, payload):
            self.inserted.append(payload)

    fake_db = FakeRedisDB()
    monkeypatch.setattr(import_redis, "EDRedis", lambda database_name: fake_db)

    import_dir = tmp_path / "ed_tinydb-export"
    import_dir.mkdir(parents=True, exist_ok=True)
    (import_dir / "Sol.json").write_text(
        json.dumps({"name": "Sol", "id64": 1}), encoding="utf-8"
    )
    (import_dir / "Sirius.json").write_text(
        json.dumps({"name": "Sirius", "id64": 2}), encoding="utf-8"
    )
    (import_dir / "ignore.txt").write_text("not json", encoding="utf-8")

    monkeypatch.setattr(
        sys, "argv", ["import_redis.py", "--import-dir", str(import_dir)]
    )
    import_redis.main()

    assert [entry["name"] for entry in fake_db.inserted] == ["Sirius", "Sol"]


def test_import_redis_raises_for_missing_dir(tmp_path, monkeypatch):
    missing_dir = tmp_path / "missing"
    monkeypatch.setattr(
        sys, "argv", ["import_redis.py", "--import-dir", str(missing_dir)]
    )
    with pytest.raises(FileNotFoundError):
        import_redis.main()


if __name__ == "__main__":
    main()
