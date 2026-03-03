import argparse
import ed_bfs
import edgis_cache
import db
from typing import Any

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
    logic(args.initial_system, args.system_count)


def logic(initial_system_name: str, number_of_systems: int) -> None:

    database = db.DB(db_filename)
    cache = edgis_cache.EDGisCache.create(database)

    # Empty destination means "walk outward" up to `number_of_systems`.
    ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        initial_system_name,
        "",
        number_of_systems,
    )


def fetch_system_info() -> Any:
    return edgis_cache.find_system_info


def fetch_neighbors() -> Any:
    edgis_cache.find_system_neighbors


if __name__ == "__main__":
    main()
