import argparse
from typing import Any

from ed_redis import EDRedis

"""Import per-system JSON exports into Redis."""


class ImportRedis:
    def __init__(self, route_service: Any, cache: Any, logging_utils: Any) -> None:
        self.route_service = route_service
        self.cache = cache
        self.logging_utils = logging_utils

    @staticmethod
    def create(route_service: Any, cache: Any, logging_utils: Any) -> "ImportRedis":
        return ImportRedis(route_service, cache, logging_utils)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import system JSON files into the Redis datastore."
    )
    parser.add_argument(
        "--import-dir",
        default="./data/ed_tinydb-export",
        help="Directory containing exported TinyDB JSON files.",
    )
    args = parser.parse_args()

    redis_db = EDRedis.create()
    redis_db.import_datasource(args.import_dir)


if __name__ == "__main__":
    main()
