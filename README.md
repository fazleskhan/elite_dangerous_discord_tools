# Elite Dangerous Tools
### Description:

Python Discord bot and CLI utilities for route lookup, system inspection,
datasource import/export, and cache operations for Elite Dangerous GIS data.


## Elite Dangerous GIS
#### Description:

The Elite Dangerous game models the Milky Way in 3D space. This project
provides GIS-oriented tools backed by EDGIS plus local datasource caching.

https://www.spansh.co.uk/dumps

https://edgis.elitedangereuse.fr/

https://github.com/elitedangereuse/edgis

### Docker Image

An image of this deployed app is available on DockerHub:

https://hub.docker.com/repository/docker/fazleskhan/public-images/tags/elite-dangerous-discord-tools/

The image externalizes configuration, logs, and database storage to
`/config`, `/logs`, and `/data`.

### Starting

Run the Discord bot process via:

`python ./src/discord_runner.py`

Run the CLI entrypoint via:

`python ./src/main.py <command> [options]`

### Configuration

#### Environment Variables

* `DISCORD_TOKEN`: required Discord bot token for `discord_runner.py` and
  `EDDiscordBot.run()`
* `DATASOURCE_TYPE`: datasource backend (`tinydb` or `redis`), default `tinydb`
* `TINYDB_NAME`: TinyDB file path override (default `./data/ed_route.db`)
* `REDIS_URL`: required when `DATASOURCE_TYPE=redis`
* `REDIS_APP_NAME`: Redis key namespace prefix (default `eddt`)
* `REDIS_MAX_CONNECTIONS`: optional Redis connection pool size override

### Logging

* Logging uses Loguru via `src/app_logging.py`.
* Runtime configuration is externalized in `config/loguru.json`.
* Config changes are hot-reloaded via watchdog file events.
* Default behavior writes datestamped file logs under `logs/`,
  archives/compresses old logs under `logs/archive`, and expires archived
  logs by retention rules.
* Console output is colorized and split by level (`info/warn` on stdout,
  `error` on stderr by default).

## Entrypoints

### CLI Entrypoint
Entrypoint: `python src/main.py <command> [options]`

Overview: Unified synchronous CLI for route search, system inspection,
cache inspection, distance checks, datasource initialization, and bulk cache
loading.

Commands and available arguments:

* `ping`
  * Overview: Health check command that returns `Pong`.
  * Arguments: none.
* `all_loaded_systems`
  * Overview: Lists all currently cached/loaded system names.
  * Arguments: none.
* `system_info`
  * Overview: Fetches and prints system info payload for a single system.
  * Arguments: `--system_name` (required).
* `path`
  * Overview: Computes a route between source and destination using BFS-based
    traversal and distance bounds.
  * Arguments: `--initial` (required), `--destination` (required),
    `--max_systems` (required, max `1000`), `--min_distance` (optional,
    default `0`), `--max_distance` (optional, default `10000`).
* `calc_systems_distance`
  * Overview: Computes Euclidean distance between two systems.
  * Arguments: `--initial` (required), `--destination` (required).
* `init_datasource`
  * Overview: Imports seed JSON records into the configured datasource.
  * Arguments: `--import_dir` (optional, default `default_init_dir`).
* `bulk_load_cache`
  * Overview: Performs breadth-first cache preloading from seed systems.
  * Arguments: `--initial_systems` (required, comma-separated seeds),
    `--max_nodes_visited` (required).

### Discord Process Entrypoint
Entrypoint: `python src/discord_runner.py`

Overview: Starts the standalone Discord bot process with environment/default
wiring via `EDDiscordBot.create()`.

Arguments and configuration:

* CLI arguments: none.
* Environment requirement: `DISCORD_TOKEN` must be configured.
* Command prefix: optional in composition; default `!`.

### Discord Command Entrypoints
Entrypoint surface: commands registered by `EDDiscordBot.register_commands()`.

Overview: Async command handlers that expose route lookup, system info,
distance, datasource init, and cache workflows in Discord.

Commands and available arguments:

* `!ping`
  * Overview: replies with latency (`Pong (<ms> ms)`).
  * Arguments: none.
* `!system_info <arg>`
  * Overview: fetches and sends the target system payload; long payloads are
    chunked.
  * Arguments: `arg` (required system name).
* `!path <initial_system_name> <destination_system_name> [max_system_count=100] [min_distance=0] [max_distance=10000]`
  * Overview: runs route search with progress updates and returns
    route/no-route result.
  * Arguments: first two required, remaining optional with defaults shown.
* `!calc_systems_distance <system_name_one> <system_name_two>`
  * Overview: computes and reports distance between two systems.
  * Arguments: both required.
* `!dump_system_cache_names`
  * Overview: dumps cached system names in chunks and reports total count.
  * Arguments: none.
* `!init_datasource [import_dir=default_init_dir]`
  * Overview: initializes datasource from import directory.
  * Arguments: optional `import_dir`.
* `!bulk_load_cache <initial_systems> <max_nodes_visited>`
  * Overview: bulk loads cache from comma-separated seeds.
  * Arguments: both required.

### Data Transfer Utility Entrypoints

Overview: Focused import/export scripts for per-system JSON transfers between
filesystem and datasource backends.

* `python src/import_tinydb.py`
  * Overview: imports JSON files into TinyDB.
  * Arguments: `--import-dir` (optional, default `default_export_dir`).
* `python src/import_redis.py`
  * Overview: imports JSON files into Redis.
  * Arguments: `--import-dir` (optional, default `default_export_dir`).
* `python src/export_tinydb.py`
  * Overview: exports TinyDB records to per-system JSON files.
  * Arguments: `--export-dir` (optional, default `default_export_dir`).
* `python src/export_redis.py`
  * Overview: exports Redis records to per-system JSON files.
  * Arguments: `--export-dir` (optional, default `default_export_dir`).

## Business Rules

Business behavior and user-visible rules are documented in [BUSINESS.md](BUSINESS.md).

## Architecture Variations

Project-specific architecture additions and overrides are documented in [ARCHITECTURE.project.md](ARCHITECTURE.project.md).

## Diagrams

### Class Diagram

Source: [docs/diagrams/class_structure.puml](docs/diagrams/class_structure.puml)

![Class Structure](docs/diagrams/class_structure.png)

### Discord Bot Sequence Diagrams

#### `run`
Source: [docs/diagrams/discord/discord_run_flow.puml](docs/diagrams/discord/discord_run_flow.puml)

![Discord Run Flow](docs/diagrams/discord/discord_run_flow.png)

#### `on_ready`
Source: [docs/diagrams/discord/discord_on_ready_flow.puml](docs/diagrams/discord/discord_on_ready_flow.puml)

![Discord On Ready Flow](docs/diagrams/discord/discord_on_ready_flow.png)

#### `ping`
Source: [docs/diagrams/discord/discord_ping_flow.puml](docs/diagrams/discord/discord_ping_flow.puml)

![Discord Ping Flow](docs/diagrams/discord/discord_ping_flow.png)

#### `system_info`
Source: [docs/diagrams/discord/discord_system_info_flow.puml](docs/diagrams/discord/discord_system_info_flow.puml)

![Discord System Info Flow](docs/diagrams/discord/discord_system_info_flow.png)

#### `path`
Source: [docs/diagrams/discord/discord_path_flow.puml](docs/diagrams/discord/discord_path_flow.puml)

![Discord Path Flow](docs/diagrams/discord/discord_path_flow.png)

#### `calc_systems_distance`
Source: [docs/diagrams/discord/discord_calc_systems_distance_flow.puml](docs/diagrams/discord/discord_calc_systems_distance_flow.puml)

![Discord Calc Systems Distance Flow](docs/diagrams/discord/discord_calc_systems_distance_flow.png)

#### `dump_system_cache_names`
Source: [docs/diagrams/discord/discord_dump_system_cache_names_flow.puml](docs/diagrams/discord/discord_dump_system_cache_names_flow.puml)

![Discord Dump System Cache Names Flow](docs/diagrams/discord/discord_dump_system_cache_names_flow.png)

#### `init_datasource`
Source: [docs/diagrams/discord/discord_init_datasource_flow.puml](docs/diagrams/discord/discord_init_datasource_flow.puml)

![Discord Init Datasource Flow](docs/diagrams/discord/discord_init_datasource_flow.png)

#### `bulk_load_cache`
Source: [docs/diagrams/discord/discord_bulk_load_cache_flow.puml](docs/diagrams/discord/discord_bulk_load_cache_flow.puml)

![Discord Bulk Load Cache Flow](docs/diagrams/discord/discord_bulk_load_cache_flow.png)

## Command Line Sequence Diagrams

#### `ping`
Source: [docs/diagrams/cli/cli_ping_flow.puml](docs/diagrams/cli/cli_ping_flow.puml)

![CLI Ping Flow](docs/diagrams/cli/cli_ping_flow.png)

#### `all_loaded_systems`
Source: [docs/diagrams/cli/cli_all_loaded_systems_flow.puml](docs/diagrams/cli/cli_all_loaded_systems_flow.puml)

![CLI All Loaded Systems Flow](docs/diagrams/cli/cli_all_loaded_systems_flow.png)

#### `system_info`
Source: [docs/diagrams/cli/cli_system_info_flow.puml](docs/diagrams/cli/cli_system_info_flow.puml)

![CLI System Info Flow](docs/diagrams/cli/cli_system_info_flow.png)

#### `path`
Source: [docs/diagrams/cli/cli_path_flow.puml](docs/diagrams/cli/cli_path_flow.puml)

![CLI Path Flow](docs/diagrams/cli/cli_path_flow.png)

#### `calc_systems_distance`
Source: [docs/diagrams/cli/cli_calc_systems_distance_flow.puml](docs/diagrams/cli/cli_calc_systems_distance_flow.puml)

![CLI Calc Systems Distance Flow](docs/diagrams/cli/cli_calc_systems_distance_flow.png)

#### `init_datasource`
Source: [docs/diagrams/cli/cli_init_datasource_flow.puml](docs/diagrams/cli/cli_init_datasource_flow.puml)

![CLI Init Datasource Flow](docs/diagrams/cli/cli_init_datasource_flow.png)

#### `bulk_load_cache`
Source: [docs/diagrams/cli/cli_bulk_load_cache_flow.puml](docs/diagrams/cli/cli_bulk_load_cache_flow.puml)

![CLI Bulk Load Cache Flow](docs/diagrams/cli/cli_bulk_load_cache_flow.png)

#### Handled CLI Error
Source: [docs/diagrams/cli/cli_handled_error_flow.puml](docs/diagrams/cli/cli_handled_error_flow.puml)

![CLI Handled Error Flow](docs/diagrams/cli/cli_handled_error_flow.png)
