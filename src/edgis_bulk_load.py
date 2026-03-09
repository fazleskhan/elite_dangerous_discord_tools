import argparse
import ed_cache
from loguru import logger
from logging_utils import setup_logging

"""Utility script to pre-populate local cache by traversing nearby systems."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-populate the local EDGIS cache by traversing nearby systems."
    )
    parser.add_argument(
        "initial_systems",
        help="Comma-separated list of starting systems (for example: Sol,Alpha Centauri)",
    )
    parser.add_argument(
        "max_nodes_visited",
        type=int,
        help="Maximum number of unique systems to visit",
    )
    args = parser.parse_args()
    initial_system_names = [
        system_name.strip()
        for system_name in args.initial_systems.split(",")
        if system_name.strip()
    ]
    logger.info(
        "Bulk load requested: initial_systems={} max_nodes_visited={}",
        initial_system_names,
        args.max_nodes_visited,
    )
    logic(initial_system_names, args.max_nodes_visited)


def logic(initial_system_names: list[str], max_nodes_visited: int) -> list[str]:
    return ed_cache.bulk_load(initial_system_names, max_nodes_visited)


if __name__ == "__main__":
    setup_logging()
    main()
