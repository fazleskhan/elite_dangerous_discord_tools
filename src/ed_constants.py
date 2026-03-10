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

# Shared payload/query keys.
value_key: str = "value"
query_param_q: str = "q"
distance_field: str = "distance"
distance: str = "distance"
system_field: str = "system"
systems_field: str = "systems"

# Common defaults and filenames.
default_init_dir: str = "./init"
json_extension: str = ".json"
default_tinydb_name: str = "./data/ed_route.db"
default_discord_log_name: str = "discord_bot.log"
default_redis_store_name: str = "eddt"

# Datasource/backend names.
datasource_type_env: str = "DATASOURCE_TYPE"
tinydb_name: str = "tinydb"
redis_name: str = "redis"

# Environment variable names.
discord_token_env: str = "DISCORD_TOKEN"
log_location_env: str = "LOG_LOCATION"
tinydb_name_env: str = "TINYDB_NAME"
redis_app_name_env: str = "REDIS_APP_NAME"
redis_url_env: str = "REDIS_URL"
redis_max_connections_env: str = "REDIS_MAX_CONNECTIONS"

# Redis URL schemes.
redis_scheme: str = "redis"
rediss_scheme: str = "rediss"
unix_scheme: str = "unix"


if __name__ == "__main__":
    main()
