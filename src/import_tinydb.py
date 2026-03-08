import argparse
import os
from pathlib import Path

from ed_tinydb import EDTinyDB

"""Import per-system JSON exports into TinyDB."""


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

    script_file = Path(__file__).resolve()
    repo_root = script_file.parent.parent
    default_db_path = str(repo_root / "data" / "ed_route.db")
    # Allow local override without changing code.
    db_path = os.getenv("DB_LOCATION", default_db_path)
    tinydb = EDTinyDB(db_path)
    tinydb.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
