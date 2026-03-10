import argparse

from ed_constants import default_export_dir, import_dir_arg
from ed_logging_utils import EDLoggingUtils

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

    tinydb = EDTinyDB.create(logging_utils=EDLoggingUtils.create())
    tinydb.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
