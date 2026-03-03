import db
import pytest
import test_data
import os

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


def test_crud_system(database):
    # initial insertion of system into db
    assert database.insert_system(test_data.sol_data) == 1
    # attempt to insert the same system again
    assert database.insert_system(test_data.sol_data) == None
    # fetch the Sol system info
    assert database.get_system("Sol") == test_data.sol_data
    # update Sol system info with neighbors
    assert database.add_neighbors(
        test_data.sol_data, test_data.sol_complete_neighbors
    ) == [1]


def test_get_all_systems(database):
    assert database.get_all_systems() != None


def test_get_system_when_record_not_available(database):
    assert database.get_system("NonExistentSystem") is None


if __name__ == "__main__":
    main()
