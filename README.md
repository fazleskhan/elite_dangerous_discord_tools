# Elite Dangerous Discord Tools

Elite Dangerous Discord Tools is a Python application for route lookup, system inspection, datasource import/export, and Discord bot access over the same route and cache services. The project uses constructor injection, protocol-based composition, and a shared Loguru-backed logging singleton wired from the application entry points.

## Implementation Summary
- `src/main.py` provides the CLI for `ping`, `path`, `system_info`, `all_loaded_systems`, `calc_systems_distance`, `init_datasource`, and `bulk_load_cache`.
- `src/ed_route.py` is the thin route-service facade over focused delegate services.
- `src/ed_route_service_factory.py` composes datasource, cache, BFS, and service collaborators.
- `src/app_logging.py` owns project-specific logging glue such as standard-logging interception, config watching, path normalization, and archive housekeeping.
- TinyDB and Redis import/export entry points reuse the same logging singleton and backend factories.
- `src/ed_discord_bot.py` exposes the same route and cache operations through Discord commands.

## Business Rules
- Business rules are documented in [BUSINESS.md](BUSINESS.md).

## Architecture Variations
- Project-specific architecture additions and overrides are documented in [ARCHITECTURE.project.md](ARCHITECTURE.project.md).

## Diagrams

### Class Structure
Source: [docs/diagrams/class_structure.puml](docs/diagrams/class_structure.puml)

![Class Structure](docs/diagrams/class_structure.png)

### CLI Entrypoint Sequence Diagrams

#### `all_loaded_systems`
Source: [docs/diagrams/cli/cli_all_loaded_systems_flow.puml](docs/diagrams/cli/cli_all_loaded_systems_flow.puml)

![CLI All Loaded Systems Flow](docs/diagrams/cli/cli_all_loaded_systems_flow.png)

#### `bulk_load_cache`
Source: [docs/diagrams/cli/cli_bulk_load_cache_flow.puml](docs/diagrams/cli/cli_bulk_load_cache_flow.puml)

![CLI Bulk Load Cache Flow](docs/diagrams/cli/cli_bulk_load_cache_flow.png)

#### `calc_systems_distance`
Source: [docs/diagrams/cli/cli_calc_systems_distance_flow.puml](docs/diagrams/cli/cli_calc_systems_distance_flow.puml)

![CLI Calc Systems Distance Flow](docs/diagrams/cli/cli_calc_systems_distance_flow.png)

#### Handled Error
Source: [docs/diagrams/cli/cli_handled_error_flow.puml](docs/diagrams/cli/cli_handled_error_flow.puml)

![CLI Handled Error Flow](docs/diagrams/cli/cli_handled_error_flow.png)

#### `init_datasource`
Source: [docs/diagrams/cli/cli_init_datasource_flow.puml](docs/diagrams/cli/cli_init_datasource_flow.puml)

![CLI Init Datasource Flow](docs/diagrams/cli/cli_init_datasource_flow.png)

#### `path`
Source: [docs/diagrams/cli/cli_path_flow.puml](docs/diagrams/cli/cli_path_flow.puml)

![CLI Path Flow](docs/diagrams/cli/cli_path_flow.png)

#### `ping`
Source: [docs/diagrams/cli/cli_ping_flow.puml](docs/diagrams/cli/cli_ping_flow.puml)

![CLI Ping Flow](docs/diagrams/cli/cli_ping_flow.png)

#### `system_info`
Source: [docs/diagrams/cli/cli_system_info_flow.puml](docs/diagrams/cli/cli_system_info_flow.puml)

![CLI System Info Flow](docs/diagrams/cli/cli_system_info_flow.png)

### Discord Entrypoint Sequence Diagrams

#### `bulk_load_cache`
Source: [docs/diagrams/discord/discord_bulk_load_cache_flow.puml](docs/diagrams/discord/discord_bulk_load_cache_flow.puml)

![Discord Bulk Load Cache Flow](docs/diagrams/discord/discord_bulk_load_cache_flow.png)

#### `calc_systems_distance`
Source: [docs/diagrams/discord/discord_calc_systems_distance_flow.puml](docs/diagrams/discord/discord_calc_systems_distance_flow.puml)

![Discord Calc Systems Distance Flow](docs/diagrams/discord/discord_calc_systems_distance_flow.png)

#### `dump_system_cache_names`
Source: [docs/diagrams/discord/discord_dump_system_cache_names_flow.puml](docs/diagrams/discord/discord_dump_system_cache_names_flow.puml)

![Discord Dump System Cache Names Flow](docs/diagrams/discord/discord_dump_system_cache_names_flow.png)

#### `init_datasource`
Source: [docs/diagrams/discord/discord_init_datasource_flow.puml](docs/diagrams/discord/discord_init_datasource_flow.puml)

![Discord Init Datasource Flow](docs/diagrams/discord/discord_init_datasource_flow.png)

#### `on_ready`
Source: [docs/diagrams/discord/discord_on_ready_flow.puml](docs/diagrams/discord/discord_on_ready_flow.puml)

![Discord On Ready Flow](docs/diagrams/discord/discord_on_ready_flow.png)

#### `path`
Source: [docs/diagrams/discord/discord_path_flow.puml](docs/diagrams/discord/discord_path_flow.puml)

![Discord Path Flow](docs/diagrams/discord/discord_path_flow.png)

#### `ping`
Source: [docs/diagrams/discord/discord_ping_flow.puml](docs/diagrams/discord/discord_ping_flow.puml)

![Discord Ping Flow](docs/diagrams/discord/discord_ping_flow.png)

#### `run`
Source: [docs/diagrams/discord/discord_run_flow.puml](docs/diagrams/discord/discord_run_flow.puml)

![Discord Run Flow](docs/diagrams/discord/discord_run_flow.png)

#### `system_info`
Source: [docs/diagrams/discord/discord_system_info_flow.puml](docs/diagrams/discord/discord_system_info_flow.puml)

![Discord System Info Flow](docs/diagrams/discord/discord_system_info_flow.png)
