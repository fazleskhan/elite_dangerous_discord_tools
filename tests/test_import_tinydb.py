import sys

import import_tinydb


def test_import_tinydb_delegates_to_backend(tmp_path, monkeypatch):  # type: ignore[no-untyped-def]
    class FakeTinyDB:
        def __init__(self) -> None:
            self.import_dir = None

        def import_datasource(self, import_dir: str) -> None:
            self.import_dir = import_dir

    fake = FakeTinyDB()
    monkeypatch.setattr(
        import_tinydb,
        "EDTinyDB",
        type(
            "FakeEDTinyDB",
            (),
            {"create": staticmethod(lambda logging_utils=None: fake)},
        ),
    )
    monkeypatch.setattr(import_tinydb.EDLoggingUtils, "create", lambda: object())
    monkeypatch.setattr(
        sys, "argv", ["import_tinydb.py", "--import-dir", str(tmp_path)]
    )

    import_tinydb.main()
    assert fake.import_dir == str(tmp_path)
