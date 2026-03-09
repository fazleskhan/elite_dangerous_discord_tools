import argparse

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

    database = EDTinyDB.create()
    database.export_datasource(args.export_dir)


if __name__ == "__main__":
    main()
