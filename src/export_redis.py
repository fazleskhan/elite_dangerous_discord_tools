import argparse

from ed_constants import default_export_dir, export_dir_arg
from ed_logging_utils import EDLoggingUtils

from ed_redis import EDRedis

"""Export cached Redis systems into per-system pretty-printed JSON files."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Redis system records into per-system JSON files."
    )
    parser.add_argument(
        export_dir_arg,
        default=default_export_dir,
        help="Output directory for exported JSON files.",
    )
    args = parser.parse_args()

    # Reuse shared logging singleton and backend factory composition.
    database = EDRedis.create(logging_utils=EDLoggingUtils.create())
    database.export_datasource(args.export_dir)


if __name__ == "__main__":
    main()
