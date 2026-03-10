import argparse

from ed_constants import default_export_dir, import_dir_arg
from ed_logging_utils import EDLoggingUtils

from ed_redis import EDRedis

"""Import per-system JSON exports into Redis."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import system JSON files into the Redis datastore."
    )
    parser.add_argument(
        import_dir_arg,
        default=default_export_dir,
        help="Directory containing exported TinyDB JSON files.",
    )
    args = parser.parse_args()

    redis_db = EDRedis.create(logging_utils=EDLoggingUtils.create())
    redis_db.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
