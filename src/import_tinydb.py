import argparse

from constants import default_export_dir, import_dir_arg
from app_logging import EDLoggingUtils

from ed_tinydb import EDTinyDB

"""Import per-system JSON exports into TinyDB."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import system JSON files into the TinyDB datastore."
    )
    parser.add_argument(
        import_dir_arg,
        default=default_export_dir,
        help="Directory containing exported Redis JSON files.",
    )
    args = parser.parse_args()

    # Reuse shared logging singleton and backend factory composition.
    logging_utils = EDLoggingUtils.create()
    logging_utils.info("import_tinydb args: import_dir={}", args.import_dir)
    tinydb = EDTinyDB.create(logging_utils=logging_utils)
    tinydb.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
