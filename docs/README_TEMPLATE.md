# Elite Dangerous Tools
### Description:

{{README:PROJECT_DESCRIPTION}}


## Elite Dangerous GIS
#### Description:

{{README:GIS_DESCRIPTION}}

### Docker Image

{{README:DOCKER_IMAGE}}

### Starting

{{README:STARTING}}

### Configuration

#### Environment Variables

{{README:ENVIRONMENT}}

### Logging

{{README:LOGGING}}

## Entrypoints

{{README:CLI_ENTRYPOINT}}

{{README:DISCORD_PROCESS_ENTRYPOINT}}

{{README:DISCORD_COMMAND_ENTRYPOINTS}}

{{README:DATA_TRANSFER_ENTRYPOINTS}}

## Code Overview

{{README:CODE_OVERVIEW}}

## Business Rules

Business behavior and user-visible rules are documented in [BUSINESS.md](BUSINESS.md).

## Architecture Variations

Project-specific architecture additions and overrides are documented in [ARCHITECTURE.project.md](ARCHITECTURE.project.md).

## Scripts

{{README:SCRIPTS}}

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
