import argparse

from ed_redis import EDRedis

"""Import per-system JSON exports into Redis."""


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

    # Load JSON export files into Redis keys/sets.
    redis_db = EDRedis.create()
    redis_db.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
