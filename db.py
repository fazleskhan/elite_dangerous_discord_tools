from tinydb import TinyDB, Query
import constants

# https://www.tutorialspoint.com/tinydb/index.htm


def main(): ...


class DB:
    def __init__(self, database_name):
        self._database_name = database_name

    def insert_system(self, system_info):
        System = Query()
        with TinyDB(self._database_name) as db:
            if not db.contains(
                System.name == system_info[constants.system_info_name_field]
            ):
                toReturn = db.insert(system_info)
                return toReturn

    def get_system(self, system_name):
        System = Query()
        with TinyDB(self._database_name) as db:
            return db.get(System.name == system_name)

    def add_neighbors(self, system_info, new_neighbors):
        System = Query()
        with TinyDB(self._database_name) as db:
            return db.update(
                {constants.system_info_neighbors_field: new_neighbors},
                System.name == system_info[constants.system_info_name_field],
            )

    def get_all_systems(self):
        with TinyDB(self._database_name) as db:
            return db.all()


if __name__ == "__main__":
    main()
