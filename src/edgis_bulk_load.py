import ed_bfs
import edgis_cache
import db
from typing import Any

"""Utility script to pre-populate local cache by traversing nearby systems."""

db_filename: str = f"{__file__.replace('src', 'data').replace('.py', '.db')}"


def main() -> None:
    initial_system_name = input("initial_system: ")
    number_of_systems = int(input("system_count: "))
    logic(initial_system_name, number_of_systems)


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
