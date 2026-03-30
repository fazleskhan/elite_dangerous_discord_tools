"""Import per-system JSON exports into Redis."""

import argparse

from ed_constants import default_export_dir, import_dir_arg
from ed_app_logging import configure_logging
from loguru import logger

from ed_redis import EDRedis


def main() -> None:
    """Import per-system JSON exports into the Redis backend.

    The entrypoint parses the import directory, configures project logging,
    constructs the Redis datasource, and forwards every discovered JSON record
    into that backend's import flow.
    """
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
    redis_db = EDRedis.create(logger=logger)
    redis_db.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
