import constants


def test_constants_export_expected_values() -> None:
    assert constants.system_info_name_field == "name"
    assert constants.system_info_neighbors_field == "neighbors"
    assert constants.default_init_dir == "./init"
    assert constants.default_export_dir == "./data/export"
    assert constants.tinydb_name == "tinydb"
    assert constants.redis_name == "redis"
    assert constants.redis_scheme == "redis"
    assert constants.rediss_scheme == "rediss"
    assert constants.unix_scheme == "unix"


def test_constants_main_is_a_noop() -> None:
    assert constants.main() is None
