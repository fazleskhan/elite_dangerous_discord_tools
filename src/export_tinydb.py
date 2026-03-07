import argparse
import json
import os
from pathlib import Path

import constants
from ed_tinydb import EDTinyDB

"""Export cached TinyDB systems into per-system pretty-printed JSON files."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export TinyDB system records into per-system JSON files."
    )
    parser.add_argument(
        "--export-dir",
        default="./data/ed_tinydb-export",
        help="Output directory for exported JSON files.",
    )
    args = parser.parse_args()

    script_file = Path(__file__).resolve()
    repo_root = script_file.parent.parent
    default_db_path = str(repo_root / "data" / "ed_route.db")
    db_path = os.getenv("DB_LOCATION", default_db_path)
    export_dir = Path(args.export_dir)

    # Ensure export target exists before writing system files.
    export_dir.mkdir(parents=True, exist_ok=True)

    database = EDTinyDB(db_path)
    # Collect system names first, then export each full record individually.
    systems = database.get_all_systems()

    for system in systems:
        system_name = system.get(constants.system_info_name_field)
        if not isinstance(system_name, str) or not system_name:
            continue

        # Fetch each full system record individually as requested.
        full_system = database.get_system(system_name)
        if full_system is None:
            continue

        safe_filename = _safe_filename(system_name)
        output_file = export_dir / f"{safe_filename}.json"
        with output_file.open("w", encoding="utf-8") as file_handle:
            json.dump(
                full_system, file_handle, indent=2, ensure_ascii=False, sort_keys=True
            )
            file_handle.write("\n")


def _safe_filename(system_name: str) -> str:
    # Keep filenames broadly readable while replacing unsafe characters.
    return "".join(
        character if character.isalnum() or character in (" ", "-", "_", ".") else "_"
        for character in system_name
    ).strip()


if __name__ == "__main__":
    main()
