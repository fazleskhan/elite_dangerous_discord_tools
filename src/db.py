from tinydb import TinyDB, Query
import constants
import logging
from typing import Any

"""TinyDB persistence helpers for cached system records."""

# https://www.tutorialspoint.com/tinydb/index.htm

logger = logging.getLogger(__name__)


SystemInfo = dict[str, Any]


def main() -> None: ...


class DB:
    def __init__(self, database_name: str):
        self._database_name = database_name
        self.logger = logger

    def insert_system(self, system_info: SystemInfo) -> int | None:
        System = Query()
        system_name = system_info[constants.system_info_name_field]
        with TinyDB(self._database_name) as db:
            # Keep one document per system name.
            if not db.contains(
                System.name == system_name
            ):
                toReturn = db.insert(system_info)
                self.logger.debug("Inserted system=%s doc_id=%s", system_name, toReturn)
                return toReturn
            self.logger.debug("Skipped duplicate system insert for system=%s", system_name)
        return None

    def get_system(self, system_name: str) -> SystemInfo | None:
        System = Query()
        with TinyDB(self._database_name) as db:
            try:
                if not db.contains(System.name == system_name):
                    self.logger.debug("Lookup system=%s found=False", system_name)
                    return None
                result = db.get(System.name == system_name)
            except Exception:
                self.logger.exception("Lookup failed for system=%s", system_name)
                return None
            self.logger.debug("Lookup system=%s found=%s", system_name, result is not None)
            return result

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> list[int]:
        System = Query()
        system_name = system_info[constants.system_info_name_field]
        with TinyDB(self._database_name) as db:
            # Attach fetched neighbor payload directly to the system document.
            updated = db.update(
                {constants.system_info_neighbors_field: new_neighbors},
                System.name == system_name,
            )
            self.logger.debug(
                "Updated neighbors for system=%s updated_rows=%s",
                system_name,
                len(updated),
            )
            return updated

    def get_all_systems(self) -> list[SystemInfo]:
        with TinyDB(self._database_name) as db:
            systems = db.all()
            self.logger.debug("Loaded all systems count=%s", len(systems))
            return systems


if __name__ == "__main__":
    main()
