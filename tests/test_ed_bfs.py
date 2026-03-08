import ed_bfs
import test_data
import shutil
import constants
import os
import edgis_cache
import datasource
import pytest

db_filename = __file__.replace("tests", "data").replace(".py", ".db")


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


def calc_systems_distance(system_name_one, system_name_two) -> float:
    if system_name_one == "Sol" and system_name_two == "Luhman 16":
        return 2
    elif system_name_one == "Alpha Centauri" and system_name_two == "Luhman 16":
        return 1
    else:
        return 0


def calc_systems_distance_return_10(system_one, system_two) -> float:
    return 10


def no_op_progress(_message: str) -> None:
    return None


expected_test_travel_list = ["Sol", "Alpha Centauri", "Luhman 16"]


def test_simple_travel():
    visited = ed_bfs.travel(
        get_system_info_test_data,
        get_neighbors_test_data,
        "Sol",
        "Luhman 16",
        10,
        0,
        100,
        calc_systems_distance,
        no_op_progress,
    )
    assert visited == expected_test_travel_list

@pytest.mark.skip(reason="the test_ed_bfs.db does not exist on fresh devcontainer")
def test_larger_local_travel_Sol_Wolf_359():

    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.normpath(os.path.join(script_dir, ".."))
    source_path = os.path.join(project_root, "init/edgis_bulk_load.db")
    shutil.copy(source_path, db_filename)

    database = datasource.DB(db_filename)
    cache = edgis_cache.EDGisCache.create(database)

    visited = ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        "Sol",
        "Wolf 359",
        10,
        0,
        100,
        calc_systems_distance_return_10,
        no_op_progress,
    )
    assert visited == ["Sol", "Wolf 359"]


@pytest.mark.skip(reason="the test_ed_bfs.db does not exist on fresh devcontainer")
def test_larger_travel_Sol_LTT_3572():

    script_dir = os.path.dirname(os.path.realpath(__file__))
    project_root = os.path.normpath(os.path.join(script_dir, ".."))
    source_path = os.path.join(project_root, "init/edgis_bulk_load.db")
    shutil.copy(source_path, db_filename)

    database = datasource.DB(db_filename)
    cache = edgis_cache.EDGisCache.create(database)

    visited = ed_bfs.travel(
        cache.find_system_info,
        cache.find_system_neighbors,
        "Sol",
        "LTT 3572",
        100,
        0,
        100,
        calc_systems_distance_return_10,
        no_op_progress,
    )
    assert visited == ["Sol", "Luhman 16", "Luyten 143-23", "LTT 3572"]


def test_travel_filters_edges_by_min_and_max_distance():
    graph = {
        "A": [
            {"name": "B", "distance": 1.0},  # below min -> excluded
            {"name": "C", "distance": 3.0},  # within range -> included
            {"name": "D", "distance": 10.0},  # above max -> excluded
        ],
        "B": [{"name": "T", "distance": 3.0}],
        "C": [{"name": "T", "distance": 4.0}],
        "D": [{"name": "T", "distance": 4.0}],
        "T": [],
    }

    def fetch_info(system_name: str):
        return {"name": system_name}

    def fetch_neighbors(system_info):
        return graph[system_info[constants.system_info_name_field]]

    distance_to_target = {
        "A": 10.0,
        "B": 8.0,
        "C": 4.0,
        "D": 12.0,
        "T": 0.0,
    }

    def calc_distance(system_one: str, system_two: str) -> float:
        return distance_to_target[system_one]

    visited = ed_bfs.travel(
        fetch_info,
        fetch_neighbors,
        "A",
        "T",
        20,
        2,
        5,
        calc_distance,
        no_op_progress,
    )
    assert visited == ["A", "C", "T"]


if __name__ == "__main__":
    main()
