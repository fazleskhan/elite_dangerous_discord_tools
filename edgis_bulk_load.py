import edgis_cache
import db
import ed_bfs
import constants
import shutil
import os


def main():
    initial_system_name = input("initial_system: ")
    number_of_systems = int(input("system_count: "))
    initialize_preloaded_db()
    logic(initial_system_name, number_of_systems)

def logic(initial_system_name, number_of_systems):
    script_dir = os.path.dirname(os.path.realpath(__file__))
    source_path = os.path.join(script_dir,
                               constants.pre_initiazlied_db_filename)

    database = db.DB(source_path)
    cache = edgis_cache.Ed_Cache(database)

    ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        initial_system_name,
        "",
        number_of_systems,
    )


def fetch_system_info():
    return edgis_cache.find_system_info


def fetch_neighbors():
    edgis_cache.find_system_neighbors


if __name__ == "__main__":
    main()
