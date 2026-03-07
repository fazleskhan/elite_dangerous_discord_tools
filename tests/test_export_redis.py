import json
import sys
from pathlib import Path

import export_redis


def main() -> None: ...


def test_export_redis_writes_pretty_json_files(tmp_path, monkeypatch):
    class FakeRedisDB:
        def get_all_systems(self):
            return [{"name": "Sol"}, {"name": "2MASS 1503/2525"}]

        def get_system(self, system_name: str):
            return {"name": system_name, "coords": {"x": 0, "y": 0, "z": 0}}

    monkeypatch.setattr(
        export_redis, "EDRedis", lambda database_name: FakeRedisDB()
    )
    export_dir = tmp_path / "ed_redis-export"
    monkeypatch.setattr(
        sys, "argv", ["export_redis.py", "--export-dir", str(export_dir)]
    )

    export_redis.main()

    sol_file = export_dir / "Sol.json"
    safe_file = export_dir / "2MASS 1503_2525.json"
    assert sol_file.exists()
    assert safe_file.exists()
    assert "\n  " in sol_file.read_text(encoding="utf-8")

    exported = json.loads(sol_file.read_text(encoding="utf-8"))
    assert exported["name"] == "Sol"


if __name__ == "__main__":
    main()
