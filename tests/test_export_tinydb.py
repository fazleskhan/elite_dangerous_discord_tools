import sys

import export_tinydb


def test_export_tinydb_delegates_to_backend(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    class FakeTinyDB:
        def __init__(self) -> None:
            self.export_dir = None

        def export_datasource(self, export_dir: str) -> None:
            self.export_dir = export_dir

    fake = FakeTinyDB()
    monkeypatch.setattr(export_tinydb, "EDTinyDB", type("FakeEDTinyDB", (), {"create": staticmethod(lambda logging_utils=None: fake)}))
    monkeypatch.setattr(export_tinydb.EDLoggingUtils, "create", lambda: object())
    monkeypatch.setattr(sys, "argv", ["export_tinydb.py", "--export-dir", str(tmp_path)])

    export_tinydb.main()
    assert fake.export_dir == str(tmp_path)
