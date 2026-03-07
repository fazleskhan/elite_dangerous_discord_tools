import argparse
import json
import os
from pathlib import Path
from typing import Any

from ed_tinydb import EDTinyDB

"""Import per-system JSON exports into TinyDB."""

SystemInfo = dict[str, Any]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import system JSON files into the TinyDB datastore."
    )
    parser.add_argument(
        "--import-dir",
        default="./data/ed_redis-export",
        help="Directory containing exported Redis JSON files.",
    )
    args = parser.parse_args()

    # Fail fast when the import source does not exist.
    import_dir = Path(args.import_dir)
    if not import_dir.exists() or not import_dir.is_dir():
        raise FileNotFoundError(f"Import directory does not exist: {import_dir}")

    script_file = Path(__file__).resolve()
    repo_root = script_file.parent.parent
    default_db_path = str(repo_root / "data" / "ed_route.db")
    db_path = os.getenv("DB_LOCATION", default_db_path)
    tinydb = EDTinyDB(db_path)

    # Import one JSON payload per file into TinyDB.
    for json_file in sorted(import_dir.glob("*.json")):
        with json_file.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        if isinstance(payload, dict):
            tinydb.insert_system(payload)


if __name__ == "__main__":
    main()
