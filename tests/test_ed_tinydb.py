import db
import ed_tinydb
import pytest
import test_data
import os
import threading
import time


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
    database.insert_system(test_data.sol_data)
    # attempt to insert the same system again
    database.insert_system(test_data.sol_data)
    # fetch the Sol system info
    assert database.get_system("Sol") == test_data.sol_data
    # update Sol system info with neighbors
    database.add_neighbors(test_data.sol_data, test_data.sol_complete_neighbors)


def test_get_all_systems(database):
    assert database.get_all_systems() != None


def test_get_system_when_record_not_available(database):
    assert database.get_system("NonExistentSystem") is None


def test_write_lock_serializes_insert_and_add_neighbors(tmp_path):
    database = db.DB(str(tmp_path / "write_lock_test.db"))
    barrier = threading.Barrier(2)
    tracker_lock = threading.Lock()
    active_writes = 0
    max_active_writes = 0
    call_count = 0

    def fake_run_async(coro):
        nonlocal active_writes, max_active_writes, call_count
        with tracker_lock:
            call_count += 1
            active_writes += 1
            max_active_writes = max(max_active_writes, active_writes)

        # Hold the critical section long enough that overlapping calls
        # would be observable if the DB write lock was not applied.
        time.sleep(0.05)

        with tracker_lock:
            active_writes -= 1

        if hasattr(coro, "close"):
            coro.close()
        return None

    database._run_async = fake_run_async  # type: ignore[method-assign]

    def do_insert() -> None:
        barrier.wait()
        database.insert_system(test_data.sol_data)

    def do_add_neighbors() -> None:
        barrier.wait()
        database.add_neighbors(test_data.sol_data, test_data.sol_complete_neighbors)

    insert_thread = threading.Thread(target=do_insert)
    add_neighbors_thread = threading.Thread(target=do_add_neighbors)
    insert_thread.start()
    add_neighbors_thread.start()
    insert_thread.join()
    add_neighbors_thread.join()

    assert call_count == 2
    assert max_active_writes == 1


def test_init_db_skips_copy_when_target_exists(tmp_path):
    database_path = str(tmp_path / "existing.db")
    tinydb_backend = ed_tinydb.EDTinyDB(database_path)
    copied: list[tuple[str, str]] = []

    tinydb_backend.init_db(
        script_file=str(tmp_path / "src" / "ed_route.py"),
        preinit_db_filename="init/edgis_bulk_load.db",
        file_exists=lambda path: path == database_path,
        copy_file=lambda src, dst: copied.append((src, dst)) or dst,
    )

    assert copied == []


def test_init_db_copies_from_repo_relative_preload_path(tmp_path):
    script_file = str(tmp_path / "src" / "ed_route.py")
    database_path = str(tmp_path / "data" / "target.db")
    preload_rel = "init/edgis_bulk_load.db"
    repo_source = str(tmp_path / "init" / "edgis_bulk_load.db")
    tinydb_backend = ed_tinydb.EDTinyDB(database_path)
    copied: list[tuple[str, str]] = []

    def fake_exists(path: str) -> bool:
        if path == database_path:
            return False
        return path == repo_source

    tinydb_backend.init_db(
        script_file=script_file,
        preinit_db_filename=preload_rel,
        file_exists=fake_exists,
        copy_file=lambda src, dst: copied.append((src, dst)) or dst,
    )

    assert copied == [(repo_source, database_path)]


if __name__ == "__main__":
    main()
