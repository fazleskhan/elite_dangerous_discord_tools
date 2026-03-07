import argparse
import json
from pathlib import Path
from typing import Any

from ed_redis import EDRedis

"""Import per-system JSON exports into Redis."""

SystemInfo = dict[str, Any]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import system JSON files into the Redis datastore."
    )
    parser.add_argument(
        "--import-dir",
        default="./data/ed_tinydb-export",
        help="Directory containing exported TinyDB JSON files.",
    )
    args = parser.parse_args()

    # Fail fast when the import source does not exist.
    import_dir = Path(args.import_dir)
    if not import_dir.exists() or not import_dir.is_dir():
        raise FileNotFoundError(f"Import directory does not exist: {import_dir}")

    redis_db = EDRedis(database_name="ed_route")

    # Import one JSON payload per file into Redis.
    for json_file in sorted(import_dir.glob("*.json")):
        with json_file.open("r", encoding="utf-8") as file_handle:
            payload = json.load(file_handle)

        if isinstance(payload, dict):
            redis_db.insert_system(payload)


if __name__ == "__main__":
    main()
