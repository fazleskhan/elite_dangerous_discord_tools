import sys

import export_tinydb


def main() -> None: ...


def test_export_tinydb_delegates_to_backend(tmp_path, monkeypatch):
    class FakeTinyDB:
        def __init__(self):
            self.export_dir = None

        def export_datasource(self, export_dir: str):
            self.export_dir = export_dir

    fake_db = FakeTinyDB()
    monkeypatch.setattr(export_tinydb, "EDTinyDB", lambda database_name: fake_db)
    export_dir = tmp_path / "ed_tinydb-export"
    monkeypatch.setattr(
        sys, "argv", ["export_tinydb.py", "--export-dir", str(export_dir)]
    )

    export_tinydb.main()

    assert fake_db.export_dir == str(export_dir)


if __name__ == "__main__":
    main()
