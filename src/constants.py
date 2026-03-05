from typing import Final

"""Shared constant keys for EDGIS payloads and local data files."""


def main() -> None: ...


# Seed database copied into a writable location on first startup.
pre_initiazlied_db_filename: Final[str] = "init/edgis_bulk_load.db"

# EDGIS system payload keys.
system_info_id64_field: Final[str] = "id64"
system_info_name_field: Final[str] = "name"
system_info_mainstar_field: Final[str] = "mainstar"
system_info_neighbors_field: Final[str] = "neighbors"
system_info_coords_field: Final[str] = "coords"
system_info_x_field: Final[str] = "x"
system_info_y_field: Final[str] = "y"
system_info_z_field: Final[str] = "z"


if __name__ == "__main__":
    main()
