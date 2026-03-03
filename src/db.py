from tinydb import TinyDB, Query
import constants
from typing import Any

"""TinyDB persistence helpers for cached system records."""

# https://www.tutorialspoint.com/tinydb/index.htm


SystemInfo = dict[str, Any]


def main() -> None: ...


class DB:
    def __init__(self, database_name: str):
        self._database_name = database_name

    def insert_system(self, system_info: SystemInfo) -> int | None:
        System = Query()
        with TinyDB(self._database_name) as db:
            # Keep one document per system name.
            if not db.contains(
                System.name == system_info[constants.system_info_name_field]
            ):
                toReturn = db.insert(system_info)
                return toReturn
        return None

    def get_system(self, system_name: str) -> SystemInfo | None:
        System = Query()
        with TinyDB(self._database_name) as db:
            return db.get(System.name == system_name)

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> list[int]:
        System = Query()
        with TinyDB(self._database_name) as db:
            # Attach fetched neighbor payload directly to the system document.
            return db.update(
                {constants.system_info_neighbors_field: new_neighbors},
                System.name == system_info[constants.system_info_name_field],
            )

    def get_all_systems(self) -> list[SystemInfo]:
        with TinyDB(self._database_name) as db:
            return db.all()


if __name__ == "__main__":
    main()
