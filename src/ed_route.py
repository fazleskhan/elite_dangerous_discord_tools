import edgis_cache
import db
import ed_bfs
import shutil
import constants
import os

db_filename = f"{__file__.replace("src", "data").replace(".py", ".db")}"


def main(): ...


def initialize_preloaded_db(source_filename):
    if not os.path.exists(db_filename):
        script_dir = os.path.realpath(__file__)
        source_path = os.path.join(script_dir, source_filename)
        shutil.copy(source_path, db_filename)


def fetch_system_info():
    return edgis_cache.find_system_info


def fetch_neighbors():
    edgis_cache.find_system_neighbors


def get_system_info(system_name):
    database = db.DB(db_filename)
    cache = edgis_cache.Ed_Cache(database)
    return cache.find_system_info(system_name)


def get_all_system_names():
    results = []
    database = db.DB(db_filename)
    system_infos = database.get_all_systems()
    for system_info in system_infos:
        results.append(system_info[constants.system_info_name_field])
    return results


def path(
    initial_system_name,
    destination_name,
    max_systems=100,
    preinit_db_filename=constants.pre_initiazlied_db_filename,
):

    initialize_preloaded_db(preinit_db_filename)

    database = db.DB(db_filename)
    cache = edgis_cache.Ed_Cache(database)

    return ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        initial_system_name,
        destination_name,
        max_systems,
    )


if __name__ == "__main__":
    main()
