from edgis import fetch_system_info
from edgis import fetch_neighbors
from edgis import EDGis
import ed_constants as constants
import pytest


def main(): ...


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        EDGis(logging_utils=None)  # type: ignore[arg-type]


def test_fetch_system_info():
    sol_data = fetch_system_info("Sol")
    assert sol_data[constants.system_info_id64_field] == 10477373803
    assert sol_data[constants.system_info_name_field] == "Sol"
    assert sol_data[constants.system_info_mainstar_field] == "G"
    assert (
        sol_data[constants.system_info_coords_field][constants.system_info_x_field]
        == 0.0
    )
    assert (
        sol_data[constants.system_info_coords_field][constants.system_info_y_field]
        == 0.0
    )
    assert (
        sol_data[constants.system_info_coords_field][constants.system_info_z_field]
        == 0.0
    )


def test_fetch_neighbors():
    sol_neighbors = fetch_neighbors(0, 0, 0)
    print(f"sol_neighbors: {sol_neighbors}")
    assert sol_neighbors[0][constants.system_info_id64_field] == 10477373803
    assert sol_neighbors[0][constants.system_info_name_field] == "Sol"
    assert sol_neighbors[0][constants.system_info_mainstar_field] == "G"
    assert (
        sol_neighbors[0][constants.system_info_coords_field][
            constants.system_info_x_field
        ]
        == 0.0
    )
    assert (
        sol_neighbors[0][constants.system_info_coords_field][
            constants.system_info_y_field
        ]
        == 0.0
    )
    assert (
        sol_neighbors[0][constants.system_info_coords_field][
            constants.system_info_z_field
        ]
        == 0.0
    )


if __name__ == "__main__":
    main()
