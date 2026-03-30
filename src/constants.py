"""Shared constant keys, defaults, and legacy aliases."""

from defaults import (
    DEFAULT_DISCORD_LOG_NAME,
    DEFAULT_EXPORT_DIR,
    DEFAULT_INIT_DIR,
    DEFAULT_REDIS_STORE_NAME,
    DEFAULT_TINYDB_NAME,
)

SYSTEM_INFO_ID64_FIELD: str = "id64"
SYSTEM_INFO_NAME_FIELD: str = "name"
SYSTEM_INFO_MAINSTAR_FIELD: str = "mainstar"
SYSTEM_INFO_NEIGHBORS_FIELD: str = "neighbors"
SYSTEM_INFO_COORDS_FIELD: str = "coords"
SYSTEM_INFO_X_FIELD: str = "x"
SYSTEM_INFO_Y_FIELD: str = "y"
SYSTEM_INFO_Z_FIELD: str = "z"

VALUE_KEY: str = "value"
QUERY_PARAM_Q: str = "q"
DISTANCE_FIELD: str = "distance"
DISTANCE: str = "distance"
SYSTEM_FIELD: str = "system"
SYSTEMS_FIELD: str = "systems"

IMPORT_DIR_ARG: str = "--import-dir"
EXPORT_DIR_ARG: str = "--export-dir"

DATASOURCE_TYPE_ENV: str = "DATASOURCE_TYPE"
TINYDB_NAME: str = "tinydb"
REDIS_NAME: str = "redis"

DISCORD_TOKEN_ENV: str = "DISCORD_TOKEN"
LOG_LOCATION_ENV: str = "LOG_LOCATION"
TINYDB_NAME_ENV: str = "TINYDB_NAME"
REDIS_APP_NAME_ENV: str = "REDIS_APP_NAME"
REDIS_URL_ENV: str = "REDIS_URL"
REDIS_MAX_CONNECTIONS_ENV: str = "REDIS_MAX_CONNECTIONS"

REDIS_SCHEME: str = "redis"
REDISS_SCHEME: str = "rediss"
UNIX_SCHEME: str = "unix"


def main() -> None: ...


def _dot_prefixed(path_value: str) -> str:
    return path_value if path_value.startswith("./") else f"./{path_value}"


system_info_id64_field: str = SYSTEM_INFO_ID64_FIELD
system_info_name_field: str = SYSTEM_INFO_NAME_FIELD
system_info_mainstar_field: str = SYSTEM_INFO_MAINSTAR_FIELD
system_info_neighbors_field: str = SYSTEM_INFO_NEIGHBORS_FIELD
system_info_coords_field: str = SYSTEM_INFO_COORDS_FIELD
system_info_x_field: str = SYSTEM_INFO_X_FIELD
system_info_y_field: str = SYSTEM_INFO_Y_FIELD
system_info_z_field: str = SYSTEM_INFO_Z_FIELD
value_key: str = VALUE_KEY
query_param_q: str = QUERY_PARAM_Q
distance_field: str = DISTANCE_FIELD
distance: str = DISTANCE
system_field: str = SYSTEM_FIELD
systems_field: str = SYSTEMS_FIELD
default_init_dir: str = _dot_prefixed(DEFAULT_INIT_DIR.as_posix())
default_export_dir: str = _dot_prefixed(DEFAULT_EXPORT_DIR.as_posix())
json_extension: str = ".json"
default_tinydb_name: str = _dot_prefixed(DEFAULT_TINYDB_NAME.as_posix())
default_discord_log_name: str = DEFAULT_DISCORD_LOG_NAME
default_redis_store_name: str = DEFAULT_REDIS_STORE_NAME
import_dir_arg: str = IMPORT_DIR_ARG
export_dir_arg: str = EXPORT_DIR_ARG
datasource_type_env: str = DATASOURCE_TYPE_ENV
tinydb_name: str = TINYDB_NAME
redis_name: str = REDIS_NAME
discord_token_env: str = DISCORD_TOKEN_ENV
log_location_env: str = LOG_LOCATION_ENV
tinydb_name_env: str = TINYDB_NAME_ENV
redis_app_name_env: str = REDIS_APP_NAME_ENV
redis_url_env: str = REDIS_URL_ENV
redis_max_connections_env: str = REDIS_MAX_CONNECTIONS_ENV
redis_scheme: str = REDIS_SCHEME
rediss_scheme: str = REDISS_SCHEME
unix_scheme: str = UNIX_SCHEME


if __name__ == "__main__":
    main()
