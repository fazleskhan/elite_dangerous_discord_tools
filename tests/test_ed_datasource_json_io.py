import json
from pathlib import Path
from typing import Any

import pytest

import ed_datasource_json_io
from tests.helpers import ThreadSafeLogger


def test_safe_filename_replaces_unsafe_characters() -> None:
    assert ed_datasource_json_io.safe_filename("Alpha/Beta:*?") == "Alpha_Beta___"


def test_import_json_records_loads_sorted_json_payloads(tmp_path: Path) -> None:
    import_dir = tmp_path / "import"
    import_dir.mkdir()
    (import_dir / "b.json").write_text('{"name":"Lave","id64":2}', encoding="utf-8")
    (import_dir / "a.json").write_text(
        '[{"name":"Sol","id64":1},"ignore-me",{"name":"Achenar","id64":3}]',
        encoding="utf-8",
    )
    (import_dir / "notes.txt").write_text("skip", encoding="utf-8")
    logger = ThreadSafeLogger()
    inserted: list[dict[str, Any]] = []

    ed_datasource_json_io.import_json_records(
        import_dir=import_dir,
        json_extension=".json",
        logger=logger,
        log_message="Importing test datasource from {} JSON files in {}",
        insert_record=inserted.append,
    )

    assert [entry["name"] for entry in inserted] == ["Sol", "Achenar", "Lave"]
    assert (
        "Importing test datasource from {} JSON files in {}",
        (2, import_dir),
    ) in logger.messages("info")


def test_import_json_records_requires_existing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Import directory does not exist"):
        ed_datasource_json_io.import_json_records(
            import_dir=tmp_path / "missing",
            json_extension=".json",
            logger=ThreadSafeLogger(),
            log_message="ignored {} {}",
            insert_record=lambda _record: None,
        )


def test_export_json_records_writes_safe_sorted_files(tmp_path: Path) -> None:
    export_dir = tmp_path / "export"
    exported_systems = [
        {"name": "Alpha/Beta"},
        {"name": ""},
        {"id64": 3},
    ]
    full_record = {"name": "Alpha/Beta", "id64": 1, "neighbors": []}

    ed_datasource_json_io.export_json_records(
        export_dir=export_dir,
        json_extension=".json",
        systems=exported_systems,
        system_name_field="name",
        get_full_system=lambda name: full_record if name == "Alpha/Beta" else None,
    )

    exported_file = export_dir / "Alpha_Beta.json"
    assert exported_file.exists()
    assert json.loads(exported_file.read_text(encoding="utf-8")) == full_record
