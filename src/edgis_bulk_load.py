import argparse
import ed_bfs
import edgis_cache
import ed_factory
from typing import Any
from loguru import logger
from logging_utils import setup_logging

"""Utility script to pre-populate local cache by traversing nearby systems."""

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
        "Bulk load requested: initial_system={} system_count={}",
        args.initial_system,
        args.system_count,
    )
    logic(args.initial_system, args.system_count)


def logic(initial_system_name: str, number_of_systems: int) -> None:
    logger.info(
        "Starting bulk load traversal from {} with max systems={}",
        initial_system_name,
        number_of_systems,
    )
    database = ed_factory.create_datasource(
        datasource_name=db_filename, datasource_type="tinydb"
    )
    cache = edgis_cache.EDGisCache.create(database)

    # Use a distant anchor destination to force outward traversal for warm-up.
    ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        initial_system_name,
        "Beagle Point",
        number_of_systems,
        0,
        10000,
        lambda _a, _b: 1.0,
        lambda message: logger.info(message),
    )
    logger.info("Bulk load traversal completed")


def fetch_system_info() -> Any:
    return edgis_cache.EDGisCache.find_system_info


def fetch_neighbors() -> Any:
    return edgis_cache.EDGisCache.find_system_neighbors


if __name__ == "__main__":
    setup_logging()
    main()
