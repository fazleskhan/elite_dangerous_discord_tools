import argparse
import ed_bfs
import edgis_cache
import db
import logging
from typing import Any
from logging_utils import resolve_log_level

"""Utility script to pre-populate local cache by traversing nearby systems."""

logger = logging.getLogger(__name__)

db_filename: str = f"{__file__.replace('src', 'data').replace('.py', '.db')}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-populate the local EDGIS cache by traversing nearby systems."
    )
    parser.add_argument(
        "initial_system",
        help="Name of the starting system (for example: Sol)",
    )
    parser.add_argument(
        "system_count",
        type=int,
        help="Maximum number of systems to traverse",
    )
    args = parser.parse_args()
    logger.info(
        "Bulk load requested: initial_system=%s system_count=%s",
        args.initial_system,
        args.system_count,
    )
    logic(args.initial_system, args.system_count)


def logic(initial_system_name: str, number_of_systems: int) -> None:
    logger.info(
        "Starting bulk load traversal from %s with max systems=%s",
        initial_system_name,
        number_of_systems,
    )
    database = db.DB(db_filename)
    cache = edgis_cache.EDGisCache.create(database)

    # Empty destination means "walk outward" up to `number_of_systems`.
    ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        initial_system_name,
        "Beagle Point",
        number_of_systems,
        lambda _a, _b: 1.0,
    )
    logger.info("Bulk load traversal completed")


def fetch_system_info() -> Any:
    return edgis_cache.find_system_info


def fetch_neighbors() -> Any:
    edgis_cache.find_system_neighbors


if __name__ == "__main__":
    logging.basicConfig(level=resolve_log_level(logging.INFO))
    main()
