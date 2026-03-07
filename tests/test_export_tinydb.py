import json
import sys

import export_tinydb


def main() -> None: ...


def test_export_tinydb_writes_pretty_json_files(tmp_path, monkeypatch):
    class FakeTinyDB:
        def get_all_systems(self):
            return [{"name": "Sol"}, {"name": "A/B"}]

        def get_system(self, system_name: str):
            return {"name": system_name, "mainstar": "G"}

    monkeypatch.setattr(export_tinydb, "EDTinyDB", lambda database_name: FakeTinyDB())
    export_dir = tmp_path / "ed_tinydb-export"
    monkeypatch.setattr(
        sys, "argv", ["export_tinydb.py", "--export-dir", str(export_dir)]
    )

    export_tinydb.main()

    sol_file = export_dir / "Sol.json"
    safe_file = export_dir / "A_B.json"
    assert sol_file.exists()
    assert safe_file.exists()
    assert "\n  " in sol_file.read_text(encoding="utf-8")

    exported = json.loads(sol_file.read_text(encoding="utf-8"))
    assert exported["name"] == "Sol"


if __name__ == "__main__":
    main()
