import sys

import import_tinydb


def main() -> None: ...


def test_import_tinydb_delegates_to_backend(tmp_path, monkeypatch):
    class FakeTinyDB:
        def __init__(self):
            self.import_dir = None

        def import_datasource(self, import_dir: str):
            self.import_dir = import_dir

    class FakeEDTinyDB:
        @staticmethod
        def create(
            datasource_name: str | None = None, *, logging_utils=None
        ):
            return fake_db

    fake_db = FakeTinyDB()
    monkeypatch.setattr(import_tinydb, "EDTinyDB", FakeEDTinyDB)
    monkeypatch.setattr(import_tinydb.EDLoggingUtils, "create", lambda: object())

    import_dir = tmp_path / "ed_redis-export"
    import_dir.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(
        sys, "argv", ["import_tinydb.py", "--import-dir", str(import_dir)]
    )
    import_tinydb.main()

    assert fake_db.import_dir == str(import_dir)


if __name__ == "__main__":
    main()
