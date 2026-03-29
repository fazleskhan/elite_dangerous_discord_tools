"""Import per-system JSON exports into TinyDB.

[README:DATA_TRANSFER_ENTRYPOINTS]
### Data Transfer Utility Entrypoints

Overview: Focused import/export scripts for per-system JSON transfers between
filesystem and datasource backends.

* `python src/import_tinydb.py`
  * Overview: imports JSON files into TinyDB.
  * Arguments: `--import-dir` (optional, default `default_export_dir`).
* `python src/import_redis.py`
  * Overview: imports JSON files into Redis.
  * Arguments: `--import-dir` (optional, default `default_export_dir`).
* `python src/export_tinydb.py`
  * Overview: exports TinyDB records to per-system JSON files.
  * Arguments: `--export-dir` (optional, default `default_export_dir`).
* `python src/export_redis.py`
  * Overview: exports Redis records to per-system JSON files.
  * Arguments: `--export-dir` (optional, default `default_export_dir`).
[/README]
"""

import argparse

from constants import default_export_dir, import_dir_arg
from app_logging import EDLoggingUtils

from ed_tinydb import EDTinyDB


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
