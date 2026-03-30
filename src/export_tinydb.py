"""Export cached TinyDB systems into per-system pretty-printed JSON files."""

import argparse

from ed_constants import default_export_dir, export_dir_arg
from ed_app_logging import configure_logging
from loguru import logger

from ed_tinydb import EDTinyDB


def main() -> None:
    """Export all TinyDB-backed system records into JSON files.

    The entrypoint parses the output directory, configures project logging,
    constructs the TinyDB backend with shared defaults, and writes one JSON
    file per stored system.
    """
    parser = argparse.ArgumentParser(
        description="Export TinyDB system records into per-system JSON files."
    )
    parser.add_argument(
        export_dir_arg,
        default=default_export_dir,
        help="Output directory for exported JSON files.",
    )
    args = parser.parse_args()

    # Reuse shared logging singleton and backend factory composition.
    configure_logging()
    logger.info("export_tinydb args: export_dir={}", args.export_dir)
    database = EDTinyDB.create(logger=logger)
    database.export_datasource(args.export_dir)


if __name__ == "__main__":
    main()
