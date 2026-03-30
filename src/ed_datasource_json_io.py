from __future__ import annotations

import json
import os
from os import PathLike
from pathlib import Path
from typing import Any


def safe_filename(value: str) -> str:
    """Convert an arbitrary system name into a filesystem-safe filename.

    Exported JSON files use system names as their base names, so this helper
    preserves readable characters and replaces everything else with underscores
    to avoid invalid or awkward paths.
    """
    return "".join(
        (character if character.isalnum() or character in (" ", "-", "_", ".") else "_")
        for character in value
    ).strip()


def import_json_records(
    *,
    import_dir: str | PathLike[str],
    json_extension: str,
    logger: Any,
    log_message: str,
    insert_record: Any,
) -> None:
    """Load JSON records from a directory into a datastore callback.

    The helper validates the import directory, iterates every matching JSON
    file, normalizes each payload into a list of records, and forwards any
    dictionary entries to the supplied insert function.
    """
    import_dir_path = Path(import_dir)
    if not import_dir_path.is_dir():
        raise FileNotFoundError(f"Import directory does not exist: {import_dir}")

    json_filenames = sorted(
        filename
        for filename in os.listdir(import_dir_path)
        if filename.endswith(json_extension)
    )
    logger.info(log_message, len(json_filenames), import_dir_path)
    for filename in json_filenames:
        json_path = import_dir_path / filename
        with json_path.open(encoding="utf-8") as json_file:
            payload = json.load(json_file)

        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            if isinstance(record, dict):
                insert_record(record)


def export_json_records(
    *,
    export_dir: str | PathLike[str],
    json_extension: str,
    systems: list[dict[str, Any]],
    system_name_field: str,
    get_full_system: Any,
) -> None:
    """Write datastore records to per-system pretty-printed JSON files.

    The helper creates the output directory, resolves each listed system to its
    full stored payload, and writes one stable JSON file per system using a
    sanitized filename.
    """
    export_dir_path = Path(export_dir)
    export_dir_path.mkdir(parents=True, exist_ok=True)

    for system in systems:
        system_name = system.get(system_name_field)
        if not isinstance(system_name, str) or not system_name:
            continue
        full_system = get_full_system(system_name)
        if full_system is None:
            continue
        output_path = export_dir_path / f"{safe_filename(system_name)}{json_extension}"
        with output_path.open("w", encoding="utf-8") as file_handle:
            json.dump(
                full_system,
                file_handle,
                indent=2,
                ensure_ascii=False,
                sort_keys=True,
            )
            file_handle.write("\n")
