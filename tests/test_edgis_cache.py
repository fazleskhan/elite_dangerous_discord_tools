import ed_factory
import pytest
import test_data
import os
import edgis_cache

test_db_filename = f"{__file__.replace("tests", "data").replace(".py", ".db")}"


def main(): ...


@pytest.fixture(scope="module")
def del_prior_database():
    if os.path.exists(test_db_filename):
        os.remove(test_db_filename)
    return "deleted"


@pytest.fixture(scope="module")
def database(del_prior_database):
    yield ed_factory.create_datasource(
        datasource_name=test_db_filename, datasource_type="tinydb"
    )


@pytest.fixture(scope="module")
def ed(database):
    def fetch_system_info_stub(system_name: str):
        if system_name == "Sol":
            return test_data.sol_data
        return None

    def fetch_neighbors_stub(x: float | int, y: float | int, z: float | int):
        if x == 0 and y == 0 and z == 0:
            return test_data.sol_complete_neighbors
        return None

    yield edgis_cache.EDGisCache.create(
        database,
        fetch_system_info_fn=fetch_system_info_stub,
        fetch_neighbors_fn=fetch_neighbors_stub,
    )


################# TESTS ####################


@pytest.mark.skip(reason="this logic is currently broken")
def test_egris_cache(ed, database):
    # check Sol not present in database
    assert database.get_system("Sol") == None

    # initial fetch system_info from EDGRIS
    assert ed.find_system_info("Sol") == test_data.sol_data

    # check Sol not present in database
    assert database.get_system("Sol") == test_data.sol_data

    # reload system_info from db
    assert ed.find_system_info("Sol") != None

    # search for invalid system
    assert ed.find_system_info("Invalid") == None

    # check Sol does not yet have neighbors
    sol_system_info = ed.find_system_info("Sol")
    with pytest.raises(KeyError):
        _ = sol_system_info["neighbors"]

    # search for Sol neighbors for the first time
    ed.find_system_neighbors(sol_system_info) == test_data.sol_complete_neighbors

    # TODO direct comparison of JSON is fragile need to find a replacement
    # check Sol info complete
    # assert database.get_system("Sol") == test_data.sol_complete_info

    # reload for Sol neighbors from db
    ed.find_system_neighbors(sol_system_info) == test_data.sol_complete_neighbors


if __name__ == "__main__":
    main()
