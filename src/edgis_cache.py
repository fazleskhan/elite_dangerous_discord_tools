from edgis import fetch_system_info, fetch_neighbors
import constants


def main(): ...


class Ed_Cache:

    def __init__(self, db):
        self.db = db

    # Provides cache abstraction layer to save system
    # information localy and reduce edgris calls
    def find_system_info(self, system_name):
        # checking if the system has already been fetched
        system_info = self.db.get_system(system_name)

        # first time requesting the system form edgis
        if not system_info:
            if system_info := fetch_system_info(system_name):
                self.db.insert_system(system_info)

        return system_info

    # Provides cache abstraction layer to save system neighbor
    # information localy and reduce edgris calls
    def find_system_neighbors(self, system_info):
        # make sure working with that latest db system_info
        db_system_info = self.db.get_system(
            system_info[constants.system_info_name_field]
        )
        neighbors = db_system_info.get(constants.system_info_neighbors_field, None)
        # If the neighbors have already been loaded don't load again
        if not neighbors:
            x = system_info[constants.system_info_coords_field][
                constants.system_info_x_field
            ]
            y = system_info[constants.system_info_coords_field][
                constants.system_info_y_field
            ]
            z = system_info[constants.system_info_coords_field][
                constants.system_info_z_field
            ]
            neighbors = fetch_neighbors(x, y, z)
            self.db.add_neighbors(system_info, neighbors)
        return neighbors


if __name__ == "__main__":
    main()
