import ed_bfs
import test_data
import shutil
import constants
import os
import edgis_cache
import db

db_filename = f"{__file__.replace("tests", "data").replace(".py", ".db")}"


def main(): ...


def get_system_info_test_data(system_name):
    if system_name == "Sol":
        return test_data.sol_data
    elif system_name == "Alpha Centauri":
        return test_data.alpha_centauri_data
    elif system_name == "Luhman 16":
        return test_data.luhman_16_data
    else:
        raise ValueError("Invalid test system_name", system_name)


def get_neighbors_test_data(system_info):
    if system_info[constants.system_info_name_field] == "Sol":
        return test_data.truncated_sol_neighbors
    elif system_info[constants.system_info_name_field] == "Alpha Centauri":
        return test_data.truncated_alpha_centauri_neighbors
    elif system_info[constants.system_info_name_field] == "Luhman 16":
        return test_data.truncated_luhman_16_neighbors
    else:
        raise ValueError(
            "Invalid test system_name", system_info[constants.system_info_name_field]
        )


expected_test_travel_list = ["Sol", "Alpha Centauri", "Luhman 16"]


def test_simple_travel():
    visited = ed_bfs.travel(
        get_system_info_test_data,
        get_neighbors_test_data,
        "Sol",
        "Luhman 16",
    )
    assert visited == expected_test_travel_list


def test_larger_local_travel_Sol_Wolf_359():

    script_dir = os.path.dirname(os.path.realpath(__file__)) + "/../data/"
    filename = constants.pre_initiazlied_db_filename
    source_path = os.path.join(script_dir, filename)
    shutil.copy(source_path, db_filename)

    database = db.DB(db_filename)
    cache = edgis_cache.EDGisCache.create(database)

    visited = ed_bfs.travel(
        cache.find_system_info, cache.find_system_neighbors, "Sol", "Wolf 359"
    )
    assert visited == ["Sol", "Wolf 359"]


def test_larger_travel_Sol_LTT_3572():

    script_dir = os.path.dirname(os.path.realpath(__file__)) + "/../data/"
    filename = constants.pre_initiazlied_db_filename
    source_path = os.path.join(script_dir, filename)
    shutil.copy(source_path, db_filename)

    database = db.DB(db_filename)
    cache = edgis_cache.EDGisCache.create(database)

    visited = ed_bfs.travel(
        cache.find_system_info, cache.find_system_neighbors, "Sol", "LTT 3572", 100
    )
    assert visited == ["Sol", "Luhman 16", "Luyten 143-23", "LTT 3572"]


if __name__ == "__main__":
    main()
