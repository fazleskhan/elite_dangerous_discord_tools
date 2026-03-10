import argparse
from typing import Any
from ed_logging_utils import EDLoggingUtils
from ed_protocols import LoggingProtocol

from ed_tinydb import EDTinyDB

"""Import per-system JSON exports into TinyDB."""


class ImportTinyDB:
    def __init__(self, route_service: Any, cache: Any, logging_utils: LoggingProtocol) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        self.route_service = route_service
        self.cache = cache
        self.logging_utils = logging_utils

    @staticmethod
    def create(route_service: Any, cache: Any, logging_utils: LoggingProtocol) -> "ImportTinyDB":
        return ImportTinyDB(route_service, cache, logging_utils)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import system JSON files into the TinyDB datastore."
    )
    parser.add_argument(
        "--import-dir",
        default="./data/ed_redis-export",
        help="Directory containing exported Redis JSON files.",
    )
    args = parser.parse_args()

    tinydb = EDTinyDB.create(logging_utils=EDLoggingUtils.create())
    tinydb.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
