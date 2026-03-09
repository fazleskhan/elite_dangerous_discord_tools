import argparse
from typing import Any

from ed_tinydb import EDTinyDB

"""Export cached TinyDB systems into per-system pretty-printed JSON files."""


class ExportTinyDB:
    def __init__(self, route_service: Any, cache: Any, logging_utils: Any) -> None:
        self.route_service = route_service
        self.cache = cache
        self.logging_utils = logging_utils

    @staticmethod
    def create(route_service: Any, cache: Any, logging_utils: Any) -> "ExportTinyDB":
        return ExportTinyDB(route_service, cache, logging_utils)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export TinyDB system records into per-system JSON files."
    )
    parser.add_argument(
        "--export-dir",
        default="./data/ed_tinydb-export",
        help="Output directory for exported JSON files.",
    )
    args = parser.parse_args()

    database = EDTinyDB.create()
    database.export_datasource(args.export_dir)


if __name__ == "__main__":
    main()
