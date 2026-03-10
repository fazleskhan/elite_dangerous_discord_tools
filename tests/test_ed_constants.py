import ed_constants


def test_constants_export_expected_values() -> None:
    assert ed_constants.system_info_name_field == "name"
    assert ed_constants.system_info_neighbors_field == "neighbors"
    assert ed_constants.default_init_dir == "./init"
    assert ed_constants.default_export_dir == "./data/export"
    assert ed_constants.tinydb_name == "tinydb"
    assert ed_constants.redis_name == "redis"
    assert ed_constants.redis_scheme == "redis"
    assert ed_constants.rediss_scheme == "rediss"
    assert ed_constants.unix_scheme == "unix"


def test_constants_main_is_a_noop() -> None:
    assert ed_constants.main() is None
