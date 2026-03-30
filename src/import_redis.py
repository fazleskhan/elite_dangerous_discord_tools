"""Import per-system JSON exports into Redis."""

import argparse

from constants import default_export_dir, import_dir_arg
from app_logging import configure_logging
from loguru import logger

from ed_redis import EDRedis


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

    # Reuse shared logging singleton and backend factory composition.
    configure_logging()
    logger.info("import_redis args: import_dir={}", args.import_dir)
    redis_db = EDRedis.create(logging_utils=logger)
    redis_db.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
