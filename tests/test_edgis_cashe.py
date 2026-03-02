import db
import pytest
import test_data
import os
import edgis_cache

# test_db_filename = __file__.replace(".py", "") + ".db"
test_db_filename = f"{__file__.replace("tests", "data").replace(".py", ".db")}"


def main(): ...


@pytest.fixture(scope="module")
def del_prior_database():
    if os.path.exists(test_db_filename):
        os.remove(test_db_filename)
    return "deleted"


@pytest.fixture(scope="module")
def database(del_prior_database):
    yield db.DB(test_db_filename)


@pytest.fixture(scope="module")
def ed(database):
    yield edgis_cache.EDGisCache.create(database)


################# TESTS ####################


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
