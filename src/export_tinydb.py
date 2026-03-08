import argparse
import os
from pathlib import Path

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
    # Allow local override without changing code.
    db_path = os.getenv("DB_LOCATION", default_db_path)

    database = EDTinyDB(db_path)
    database.export_datasource(args.export_dir)


if __name__ == "__main__":
    main()
