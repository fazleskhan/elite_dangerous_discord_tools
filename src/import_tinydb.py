import argparse

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

    tinydb = EDTinyDB.create()
    tinydb.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
