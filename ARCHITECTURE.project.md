# Project-Specific Architecture Companion

Use this file with [ARCHITECTURE.md](ARCHITECTURE.md) as the repository-specific infrastructure prompt for Elite Dangerous Discord Tools.

## Purpose
- Regenerate this repository with the shared contract from `ARCHITECTURE.md` plus the project-specific constraints below.
- Treat these entries as concise implementation prompts for local infrastructure code.
- If a prompt here conflicts with `ARCHITECTURE.md`, this file wins for this repository.

## Source Module Naming
- Keep the CLI command entrypoint modules [src/main.py](src/main.py), [src/discord_runner.py](src/discord_runner.py), [src/import_tinydb.py](src/import_tinydb.py), [src/import_redis.py](src/import_redis.py), [src/export_tinydb.py](src/export_tinydb.py), and [src/export_redis.py](src/export_redis.py) without adding an `ed_` filename prefix.
- For every other top-level Python source file in `src/`, prepend `ed_` to the filename when it does not already start with `ed_`.
- If a top-level Python source filename in `src/` already starts with `ed_`, keep that filename unchanged.
- Preserve [src/__init__.py](src/__init__.py) as the package marker file required by Python packaging semantics.
- Rename tests under `tests/` so their filenames continue to reflect the source modules they primarily cover.

## Entry Points
- Keep [src/main.py](src/main.py) as the synchronous CLI entry point.
- Keep [src/ed_discord_bot.py](src/ed_discord_bot.py) as the Discord-triggered entry point module.
- Keep [src/discord_runner.py](src/discord_runner.py) as the standalone Discord process launcher.
- Keep [src/import_tinydb.py](src/import_tinydb.py), [src/import_redis.py](src/import_redis.py), [src/export_tinydb.py](src/export_tinydb.py), and [src/export_redis.py](src/export_redis.py) as focused import/export utility entry points.
- When entry points change, regenerate matching per-entrypoint sequence diagrams.

## Diagram Layout
- Put CLI entrypoint sequence sources under `docs/diagrams/cli/`.
- Put Discord entrypoint sequence sources under `docs/diagrams/discord/`.
- Put shared structure diagrams under `docs/diagrams/`.
- Remove stale diagrams when a clearer authoritative source replaces them.

## Config Watching
- Implement logging config watching in [src/ed_app_logging.py](src/ed_app_logging.py).
- Use `_LoguruConfigWatcher` as the single process-wide watcher for loading, applying, and reloading Loguru config.
- Watch the parent directory of `config/loguru.json` with `watchdog` and ignore unrelated filesystem events.
- Guard reloads with file-mtime checks and locking so duplicate events do not cause overlapping reconfiguration.
- Always perform the initial config load, even when file watching is disabled.

## Async Boundaries
- Keep the CLI boundary synchronous and bridge async route work with `asyncio.run(...)`.
- Keep Discord command handlers as `async def` functions running inside the Discord event loop.
- Normalize sync and awaitable collaborator results in [src/ed_discord_bot.py](src/ed_discord_bot.py) through `_resolve(...)`.
- Send off-loop Discord progress updates with `asyncio.run_coroutine_threadsafe(...)`.
- Log progress-send failures without aborting the surrounding command coroutine.
- Keep async concerns at integration boundaries, not in core business services.

## Route Composition
- Keep [src/ed_route.py](src/ed_route.py) as a thin facade that delegates work to focused services instead of owning route, import, cache, or distance logic directly.
- Build the fully wired route stack in [src/ed_route_service_factory.py](src/ed_route_service_factory.py).
- Compose the route stack from datasource selection, EDGIS-backed cache creation, system-info service, all-system-names service, distance service, BFS traversal, path service, and bulk-load service.
- Keep [src/ed_path_service.py](src/ed_path_service.py) responsible for offloading blocking BFS work onto a worker thread with `asyncio.to_thread(...)` so async callers remain responsive.
- Treat [src/ed_route_services.py](src/ed_route_services.py) as a temporary legacy re-export module; do not introduce new compatibility modules that extend this pattern.

## Datasource Selection
- Implement datasource selection in [src/ed_datasource_factory.py](src/ed_datasource_factory.py).
- Resolve datasource type in the order explicit argument, environment variable, then TinyDB default.
- Support only the `tinydb` and `redis` datasource types and fail fast on invalid values.
- Keep datasource creation lazy so backend modules are imported only when selected.
- Reuse the shared logging singleton when constructing datasource instances.

## Redis Integration
- Implement Redis datasource behavior in [src/ed_redis.py](src/ed_redis.py).
- Use Redis as an optional persistence backend for cached system records, imports, exports, and lookup state.
- Resolve Redis connection settings from constructor arguments first, then environment variables.
- Require and validate `REDIS_URL` for Redis-backed operation.
- Namespace Redis keys by datasource or app name so multiple instances can share one Redis safely.
- Use `redis.asyncio` internally but expose sync-friendly methods by bridging async work with `asyncio.run(...)` or a worker thread when a loop already exists.
- Bound connection growth with a configurable max-connections setting.
- Coordinate shutdown with close guards plus `atexit` registration.
- Keep import/export behavior aligned with per-system JSON files.

## TinyDB Integration
- Implement TinyDB datasource behavior in [src/ed_tinydb.py](src/ed_tinydb.py).
- Use TinyDB as the local file-backed persistence backend for cached system records.
- Resolve the datasource path from constructor input first, then environment-backed ed_defaults, and create parent directories before use.
- Use `SmartCacheTinyDB` with `SmartCacheTable` and `JSONStorage`.
- Wrap TinyDB access in `AIOTinyDB` for async-compatible usage, then bridge back to sync-friendly methods in `EDTinyDB`.
- Maintain in-memory per-system caching and all-systems caching for hot lookup paths.
- Serialize writes with locks to protect single-process TinyDB state.
- Keep import/export behavior aligned with per-system JSON files.

## EDGIS Webservice Integration
- Implement EDGIS HTTP access in [src/ed_edgis.py](src/ed_edgis.py).
- Use `EDGis` as the only direct HTTP gateway for EDGIS-backed lookups.
- Use `aiohttp` with a bounded total timeout.
- Bridge async HTTP work back to synchronous callers with `asyncio.run(...)` or a worker thread when a loop already exists.
- Limit direct EDGIS calls to the coords and neighbors endpoints needed for cache misses and route expansion.
- Convert transport and timeout failures into logged `None` results at the gateway boundary.
- Inject EDGIS fetch functions into higher-level services instead of making ad hoc HTTP calls elsewhere.

## Documentation Split
- Keep shared cross-project rules in [ARCHITECTURE.md](ARCHITECTURE.md).
- Keep repository-specific infrastructure prompts in [ARCHITECTURE.project.md](ARCHITECTURE.project.md).
- Keep feature and business behavior in [BUSINESS.md](BUSINESS.md).
- Use [dev-requirements.txt](dev-requirements.txt) as this repository's local-development dependency manifest for testing, linting, typing, profiling, and formatting tools.
- Keep the libraries listed in [dev-requirements.txt](dev-requirements.txt) in alphabetical order.
- When reloading Python dependencies in a development environment for this repository, install both [requirements.txt](requirements.txt) and [dev-requirements.txt](dev-requirements.txt).
- Add new Python dependencies to [dev-requirements.txt](dev-requirements.txt) by default unless they are required while the application is deployed in production, in which case add them to [requirements.txt](requirements.txt).
- In [dev-requirements.txt](dev-requirements.txt), keep a short comment above every listed library describing what the library does and how this project uses it.

## Script Documentation
- Keep a dedicated scripts section in [README.md](README.md) that documents the files in the `scripts/` directory.
- Use that README section to describe what each script does and how to use it.
- When a script is added, updated, or removed from `scripts/`, update [README.md](README.md) in the same change.
- Keep the authoritative script descriptions as comments inside each script file.
- Generate the README scripts section from those in-script comments via `scripts/generated_readme.py`.
