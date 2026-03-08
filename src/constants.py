"""Shared constant keys for EDGIS payloads and local data files."""


def main() -> None: ...


# EDGIS system payload keys.
# Keep these values aligned with upstream EDGIS response field names.
system_info_id64_field: str = "id64"
system_info_name_field: str = "name"
system_info_mainstar_field: str = "mainstar"
system_info_neighbors_field: str = "neighbors"
system_info_coords_field: str = "coords"
system_info_x_field: str = "x"
system_info_y_field: str = "y"
system_info_z_field: str = "z"


if __name__ == "__main__":
    main()
