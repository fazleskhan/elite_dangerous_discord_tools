import argparse

from ed_redis import EDRedis

"""Export cached Redis systems into per-system pretty-printed JSON files."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Redis system records into per-system JSON files."
    )
    parser.add_argument(
        "--export-dir",
        default="./data/ed_redis-export",
        help="Output directory for exported JSON files.",
    )
    args = parser.parse_args()

    # Export each cached system into a standalone JSON file.
    database = EDRedis.create()
    database.export_datasource(args.export_dir)


if __name__ == "__main__":
    main()
