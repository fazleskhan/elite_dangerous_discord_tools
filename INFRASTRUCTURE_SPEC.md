# Infrastructure Reconstruction Spec

This document is a reconstruction-grade specification for rebuilding the `src/` tree of Elite Dangerous Discord Tools from an empty directory. It describes the exact source-file inventory, responsibilities, interfaces, wiring rules, runtime dependencies, and generated artifacts required to faithfully recreate the current infrastructure implementation.

Use this document together with [BUSINESS_SPEC.md](BUSINESS_SPEC.md). This file describes how the system is structured and wired. `BUSINESS_SPEC.md` describes what the system must do.

## 1. Repository-Level Outcome

Recreate a Python project that provides:
- a synchronous CLI entrypoint
- a Discord bot process entrypoint
- focused import and export utility entrypoints
- a route-search service stack
- selectable TinyDB or Redis persistence chosen by environment
- EDGIS-backed cache misses for system and neighbor lookups
- Loguru-based logging with hot-reloading configuration

The rebuilt project must place the user-facing implementation under `src/`.

## 2. Source File Inventory

Recreate exactly these top-level Python files under `src/`:

- `__init__.py`
- `discord_runner.py`
- `ed_app_logging.py`
- `ed_bfs_algo.py`
- `ed_bulk_load_algo.py`
- `ed_bulk_load_cache_service.py`
- `ed_calc_systems_distance_service.py`
- `ed_cli_command_runner.py`
- `ed_cli_parser.py`
- `ed_constants.py`
- `ed_datasource_factory.py`
- `ed_datasource_json_io.py`
- `ed_defaults.py`
- `ed_discord_bot.py`
- `ed_discord_command_registry.py`
- `ed_discord_message_utils.py`
- `ed_edgis.py`
- `ed_edgis_cache.py`
- `ed_get_all_system_names_service.py`
- `ed_get_system_info_service.py`
- `ed_init_datasource_service.py`
- `ed_loguru_config_loader.py`
- `ed_loguru_runtime.py`
- `ed_path_service.py`
- `ed_protocols.py`
- `ed_redis.py`
- `ed_route.py`
- `ed_route_service_factory.py`
- `ed_sync_async_bridge.py`
- `ed_tinydb.py`
- `export_redis.py`
- `export_tinydb.py`
- `import_redis.py`
- `import_tinydb.py`
- `main.py`

Do not recreate `ed_route_services.py`. It was a removed legacy re-export shim.

## 3. File Naming Rules

- Keep `main.py`, `discord_runner.py`, `import_tinydb.py`, `import_redis.py`, `export_tinydb.py`, and `export_redis.py` unprefixed.
- Prefix every other top-level Python file in `src/` with `ed_` unless it is `__init__.py`.
- Preserve `src/__init__.py` as the package marker.

## 4. Entrypoints

### 4.1 CLI

`src/main.py` is the synchronous CLI entrypoint.

Responsibilities:
- configure logging
- build the argparse parser
- log parsed CLI parameters
- compose an `EDMain` instance
- dispatch to the command runner
- translate handled CLI errors into exit code `1` without traceback

### 4.2 Discord Process

`src/discord_runner.py` is the standalone Discord process launcher.

Responsibilities:
- configure logging
- log startup
- build `EDDiscordBot` from defaults
- run the bot
- log and re-raise unexpected startup failures

### 4.3 Import/Export Utilities

The following are focused command-line entrypoints:
- `src/import_tinydb.py`
- `src/import_redis.py`
- `src/export_tinydb.py`
- `src/export_redis.py`

Each must:
- configure logging
- parse only the one relevant directory flag
- create the correct datasource backend directly
- perform the requested import or export operation

## 5. Primary Dependency Graph

Recreate this composition shape:

1. `main.py` and `discord_runner.py` are entrypoint composition roots.
2. Both rely on `ed_app_logging.py` for logging setup.
3. Route-service composition is centralized in `EDRouteServiceFactory`.
4. `EDRouteServiceFactory` uses `EDDatasourceFactory` to choose storage.
5. `EDDatasourceFactory` lazily imports and creates either `EDTinyDB` or `EDRedis`.
6. `EDGis` provides direct HTTP access to EDGIS.
7. `EDGisCache` combines datasource storage with EDGIS fetchers for cache-through reads.
8. Focused services sit above datasource or cache:
   - `EDInitDatasourceService`
   - `EDGetSystemInfoService`
   - `EDGetAllSystemNamesService`
   - `EDCalcSystemsDistanceService`
   - `EDPathService`
9. Algorithms sit below the high-level route facade:
   - `EDBfsAlgo`
   - `EDBulkLoadAlgo`
10. `EDRouteService` is a thin facade over those focused services.
11. `EDMain` and `EDDiscordBot` depend on `EDRouteService` rather than lower-level objects.

## 6. Protocols and Type Contracts

Put all core protocol definitions in `src/ed_protocols.py`.

Required aliases:
- `SystemInfo = dict[str, Any]`
- `FetchInfoFn`
- `FetchSystemInfoFn`
- `FetchNeighborsFn`
- `DistanceFn`
- `ProgressFn`

Required protocols:
- `IDatasource`
- `ICache`
- `ILogger`
- `IGis`
- `IRouteService`
- `IDiscordContext`
- `IDiscordBot`
- `IBfs`
- `IBulkLoad`
- `IInitDatasource`
- `IGetSystemInfo`
- `IGetAllSystemNames`
- `IPathService`
- `ICalcSystemsDistance`

Required alias exports:
- `DatasourceProtocol`
- `CacheProtocol`
- `LoggingProtocol`
- `GisProtocol`
- `RouteServiceProtocol`
- `DiscordContextProtocol`
- `DiscordBotProtocol`
- `BfsProtocol`
- `BulkLoadProtocol`
- `InitDatasourceProtocol`
- `GetSystemInfoProtocol`
- `GetAllSystemNamesProtocol`
- `PathProtocol`
- `CalcSystemsDistanceProtocol`

Every class that collaborates with another component must depend on these protocols rather than concrete implementations where practical.

## 7. Constants and Defaults

### 7.1 `src/ed_defaults.py`

Define shared default values as constants, including:
- `DEFAULT_INIT_DIR = Path("./init")`
- `DEFAULT_EXPORT_DIR = Path("./data/export")`
- `DEFAULT_TINYDB_NAME = Path("./data/ed_route.db")`
- `DEFAULT_DISCORD_LOG_NAME = "discord_bot.log"`
- `DEFAULT_REDIS_STORE_NAME = "eddt"`
- `DEFAULT_LOGURU_CONFIG_PATH = Path("config/loguru.json")`
- `DEFAULT_APPLICATION_LOG_PATH = Path("logs/application.log")`
- `DEFAULT_LOG_ARCHIVE_DIR = Path("logs/archive")`
- `DEFAULT_LOG_TEXT_FORMAT`
- `DEFAULT_LOG_COLOR_FORMAT`
- `DEFAULT_LOGURU_CONFIG`

The default Loguru config must define:
- stdout sink at `INFO`
- stderr sink at `ERROR`
- file sink at `INFO`
- daily rotation at `00:00`
- archive-after-days `7`
- archive-retention-days `30`
- watch enabled by default

### 7.2 `src/ed_constants.py`

Define shared string constants and lowercase aliases, including:
- system payload field names
- import/export argument names
- datasource env-var names
- datasource type names
- Redis scheme names
- lower-case aliases such as `default_init_dir`, `tinydb_name`, `redis_name`, etc.

## 8. Logging Infrastructure

### 8.1 Logging Library

Use Loguru as the application logger.

### 8.2 `src/ed_app_logging.py`

This file owns only project-specific logging glue:
- Loguru configuration loading
- standard-library logging interception
- path normalization
- log archival and retention cleanup
- config-file watching

Required elements:
- `InterceptHandler` forwarding standard-library logging into Loguru
- `configure_logging()`
- `configure_standard_logging_intercept()`
- `apply_loguru_config()`
- `_LoguruConfigWatcher`
- `_ConfigFileEventHandler`

Behavior:
- one process-wide watcher singleton
- initial config always applied
- file watching uses `watchdog`
- watched target is the parent directory of `config/loguru.json`
- reloads are guarded by mtime checks plus a lock
- stale log files older than 7 days are gzipped into `logs/archive/`
- archives older than 30 days are deleted

### 8.3 Supporting Logging Modules

`src/ed_loguru_config_loader.py` must provide:
- deep merge of nested dicts
- config-file loading from JSON or optional `loguru-config`

`src/ed_loguru_runtime.py` must provide:
- level-based filter construction
- sink application for stdout, stderr, and file logging

## 9. CLI Infrastructure

### 9.1 `src/ed_cli_parser.py`

Build a single shared `argparse.ArgumentParser` with:
- positional `command`
- options:
  - `--import_dir`
  - `--initial`
  - `--destination`
  - `--max_systems`
  - `--min_distance`
  - `--max_distance`
  - `--system_name`
  - `--initial_systems`
  - `--max_nodes_visited`

### 9.2 `src/ed_cli_command_runner.py`

Provide:
- `CLIHandledError`
- `elapsed_ms()`
- `raise_usage_error()`
- `log_handled_error()`
- `log_execution_time()`
- `run_command()`

Behavior:
- validate command-specific arguments
- log command receipt
- route work to `EDMain`
- format handled usage errors without traceback

### 9.3 `src/main.py`

Define:
- `EDMain`
- top-level `main()`

`EDMain` must wrap:
- `ping`
- `get_all_system_names`
- `calc_route`
- `calc_systems_distance`
- `get_system_info`
- `init_datasource`
- `bulk_load_cache`

`calc_route()` must bridge async route work with `asyncio.run(...)`.

## 10. Discord Infrastructure

### 10.1 `src/ed_discord_bot.py`

Define `EDDiscordBot` as an IoC wrapper around a `discord.ext.commands.Bot`.

Required responsibilities:
- validate injected bot, token, route service, and logger
- register `on_ready`
- register command handlers
- support sync and async route-service collaborators through `_resolve()`
- default command prefix `"!"`
- default intents enabling `message_content` and `members`

Required public command handlers:
- `ping`
- `system_info`
- `calc_systems_distance`
- `path`
- `dump_system_cache_names`
- `init_datasource`
- `bulk_load_cache`
- `run`

### 10.2 `src/ed_discord_command_registry.py`

Register Discord command wrappers against the underlying bot object, preserving the command names and signatures expected by `discord.ext.commands`.

### 10.3 `src/ed_discord_message_utils.py`

Provide:
- `chunked_sequence()`
- `send_chunked_text()`
- `DiscordProgressReporter`

`DiscordProgressReporter` must:
- log progress messages
- send progress messages onto the event loop using `asyncio.run_coroutine_threadsafe`
- log send failures without crashing the surrounding workload

## 11. Route Stack

### 11.1 `src/ed_route.py`

Define `EDRouteService` as a thin facade. It must not contain route-search, distance, or datasource logic directly. It must delegate to focused services injected into the constructor.

### 11.2 `src/ed_route_service_factory.py`

This is the route-layer composition root.

It must:
- accept optional overrides for datasource, cache, BFS, and focused services
- create the missing layers in dependency order
- preserve any caller-supplied collaborators

Default composition order:
1. datasource
2. init-datasource service
3. EDGIS gateway
4. cache
5. get-system-info service
6. get-all-system-names service
7. calc-distance service
8. BFS algorithm
9. path service
10. bulk-load algorithm
11. final `EDRouteService`

### 11.3 Focused Service Files

Recreate these classes:
- `EDInitDatasourceService` in `ed_init_datasource_service.py`
- `EDGetSystemInfoService` in `ed_get_system_info_service.py`
- `EDGetAllSystemNamesService` in `ed_get_all_system_names_service.py`
- `EDCalcSystemsDistanceService` in `ed_calc_systems_distance_service.py`
- `EDPathService` in `ed_path_service.py`
- `EDBulkLoadCacheService` in `ed_bulk_load_cache_service.py`

`EDPathService` must offload blocking BFS work with `asyncio.to_thread(...)`.

## 12. Route and Bulk-Load Algorithms

### 12.1 `src/ed_bfs_algo.py`

Implement breadth-first traversal with injected:
- fetch-system-info function
- fetch-neighbors function
- distance function
- logger

The BFS algorithm must:
- reconstruct the final path from a parent map
- support min and max hop distance filtering
- prune nodes that become at least 5 percent farther from the destination than the best seen distance
- emit throttled progress messages

### 12.2 `src/ed_bulk_load_algo.py`

Implement frontier-based graph expansion with injected:
- fetch-system-info function
- fetch-neighbors function
- logger

The bulk-load algorithm must:
- normalize seed names
- avoid duplicate visits
- preserve deterministic visit order
- use a `ThreadPoolExecutor`
- size the pool from physical CPU count with a logical-core fallback
- reuse sufficiently complete neighbor payloads directly
- emit periodic progress at exact 512-system boundaries

## 13. Datasource Selection and Shared JSON I/O

### 13.1 `src/ed_datasource_factory.py`

Provide:
- `EDDatasourceFactory`
- `resolve_datasource_type()`
- `create_datasource()`

Behavior:
- `DATASOURCE_TYPE` resolution order is explicit argument, env var, then TinyDB default
- supported values are only `tinydb` and `redis`
- backend imports are lazy

### 13.2 `src/ed_datasource_json_io.py`

Provide shared helpers:
- `safe_filename()`
- `import_json_records()`
- `export_json_records()`

These helpers are shared by TinyDB and Redis import/export flows.

## 14. TinyDB Backend

### 14.1 `src/ed_tinydb.py`

Recreate:
- `SmartCacheTinyDB`
- `AIOTinyDB`
- `EDTinyDB`

Required behavior:
- local file-backed persistence
- use `SmartCacheTable` and `JSONStorage`
- create parent directories before use
- maintain in-memory per-system cache plus all-systems cache
- serialize writes with locks
- bridge async-style helpers back into sync public methods with `run_async_from_sync()`

## 15. Redis Backend

### 15.1 `src/ed_redis.py`

Recreate `EDRedis`.

Required behavior:
- use `redis.asyncio` internally
- expose sync-friendly public methods
- resolve settings from explicit args first, then env vars
- validate `REDIS_URL`
- support only `redis`, `rediss`, and `unix` schemes
- require a host for `redis` and `rediss`
- namespace keys by datasource name
- maintain a companion Redis set for system-name enumeration
- close short-lived clients after each logical operation
- register a close hook with `atexit`

## 16. Sync/Async Bridge

`src/ed_sync_async_bridge.py` must provide `run_async_from_sync()`.

Behavior:
- use `asyncio.run()` when no event loop is active
- if a loop is already running, execute the coroutine in a worker thread and return the result synchronously

## 17. EDGIS Integration

### 17.1 `src/ed_edgis.py`

Recreate `EDGis`.

Required behavior:
- use `aiohttp`
- use a 15-second total timeout
- expose sync-friendly `fetch_system_info()` and `fetch_neighbors()` methods
- bridge async HTTP work back to sync callers
- call only:
  - `https://edgis.elitedangereuse.fr/coords`
  - `https://edgis.elitedangereuse.fr/neighbors`

### 17.2 `src/ed_edgis_cache.py`

Recreate `EDGisCache`.

Required behavior:
- datasource-backed cache-through reads
- persist cache misses into the datasource
- fetch system info by name
- fetch neighbors from a system's coordinates

## 18. Runtime Dependencies

The runtime dependency manifest must be `requirements.txt`, alphabetically ordered, with one descriptive comment above each package entry.

Required packages:
- `aiohttp`
- `aiotinydb`
- `autologging`
- `discord`
- `loguru`
- `loguru-config`
- `psutil`
- `python-dotenv`
- `redis[hiredis]`
- `tinydb`
- `tinydb-smartcache`
- `ujson`
- `watchdog`

## 19. Development Dependencies

The development dependency manifest must be `dev-requirements.txt`, alphabetically ordered, with one descriptive comment above each package entry.

Required packages:
- `austin-python`
- `black`
- `coverage`
- `mypy`
- `pyright`
- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `pyupgrade`
- `refurb`
- `ruff`
- `tuna`

## 20. Environment Variables

Recreate support for these environment variables:
- `DISCORD_TOKEN`
- `DATASOURCE_TYPE`
- `TINYDB_NAME`
- `REDIS_URL`
- `REDIS_APP_NAME`
- `REDIS_MAX_CONNECTIONS`
- `LOG_LOCATION` if preserved for compatibility

Behavior:
- load `.env` in the CLI, Discord, datasource, and logging setup flows where configuration may be needed

## 21. Documentation and Generated Artifacts

Recreate and maintain:
- `README.md` as a generated file
- `docs/README_TEMPLATE.md`
- PlantUML source diagrams under `docs/diagrams/`
- PNG siblings for those diagrams

README generation requirements:
- source narrative content from tagged module docstrings and script comment blocks
- source code-overview sections from class and method docstrings
- source library lists from `requirements.txt` and `dev-requirements.txt`
- generate with `python scripts/generate_readme.py`

## 22. Quality Gates

After rebuilding the project, the implementation must be able to pass:
- `black .`
- `ruff check .`
- `pyright`
- `npm run spellcheck`
- `pytest -q`

## 23. Non-Negotiable Implementation Rules

- Use constructor injection and protocols for collaborator boundaries.
- Use guard clauses and fail-fast validation.
- Add a docstring to every class and every method.
- Keep clarifying comments accurate when code changes.
- Do not add shim or compatibility modules.
- Do not use `print()` for application output.
- Keep logging, docs, dependency manifests, and diagrams in sync with source changes.
