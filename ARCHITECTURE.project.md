# Project-Specific Architecture Companion

Use this file with [ARCHITECTURE.md](ARCHITECTURE.md) for Elite Dangerous Discord Tools.

## Legend
- `➕ Extends`: adds repository-specific detail to the shared contract.
- `⚠ Overrides`: replaces a shared-contract default for this repository.

## Source Module Naming
- `⚠ Overrides` Keep [src/main.py](src/main.py), [src/discord_runner.py](src/discord_runner.py), [src/import_tinydb.py](src/import_tinydb.py), [src/import_redis.py](src/import_redis.py), [src/export_tinydb.py](src/export_tinydb.py), and [src/export_redis.py](src/export_redis.py) unprefixed.
- `⚠ Overrides` Prefix every other top-level Python file in `src/` with `ed_` unless it already starts with `ed_`.
- `➕ Extends` Preserve [src/__init__.py](src/__init__.py) as the package marker.
- `➕ Extends` Keep test filenames aligned with the primary source modules they cover.

## Entrypoints and Diagrams
- `➕ Extends` Treat [src/main.py](src/main.py) as the synchronous CLI entrypoint.
- `➕ Extends` Treat [src/ed_discord_bot.py](src/ed_discord_bot.py) as the Discord command entrypoint module.
- `➕ Extends` Treat [src/discord_runner.py](src/discord_runner.py) as the standalone Discord process launcher.
- `➕ Extends` Treat [src/import_tinydb.py](src/import_tinydb.py), [src/import_redis.py](src/import_redis.py), [src/export_tinydb.py](src/export_tinydb.py), and [src/export_redis.py](src/export_redis.py) as focused import/export utility entrypoints.
- `➕ Extends` Put CLI sequence diagrams under `docs/diagrams/cli/`, Discord sequence diagrams under `docs/diagrams/discord/`, and shared structure diagrams under `docs/diagrams/`.

## Logging Config Watching
- `➕ Extends` Implement logging config watching in [src/ed_app_logging.py](src/ed_app_logging.py).
- `➕ Extends` Use `_LoguruConfigWatcher` as the single process-wide watcher.
- `➕ Extends` Watch the parent directory of `config/loguru.json` and ignore unrelated filesystem events.
- `➕ Extends` Guard reloads with file-mtime checks and locking.
- `➕ Extends` Always perform the initial config load even when watching is disabled.

## Async Boundaries
- `➕ Extends` Keep the CLI boundary synchronous and bridge async route work with `asyncio.run(...)`.
- `➕ Extends` Keep Discord command handlers as `async def` functions running inside the Discord event loop.
- `➕ Extends` Normalize sync and awaitable collaborator results in [src/ed_discord_bot.py](src/ed_discord_bot.py) through `_resolve(...)`.
- `➕ Extends` Send off-loop Discord progress updates with `asyncio.run_coroutine_threadsafe(...)`.
- `➕ Extends` Log progress-send failures without aborting the surrounding command.
- `➕ Extends` Keep async concerns at integration boundaries, not in core business services.

## Route Composition
- `➕ Extends` Keep [src/ed_route.py](src/ed_route.py) as a thin facade over focused services.
- `➕ Extends` Build the route stack in [src/ed_route_service_factory.py](src/ed_route_service_factory.py).
- `➕ Extends` Compose the stack from datasource selection, EDGIS-backed cache creation, system-info service, all-system-names service, distance service, BFS traversal, path service, and bulk-load service.
- `➕ Extends` Keep [src/ed_path_service.py](src/ed_path_service.py) responsible for offloading blocking BFS work with `asyncio.to_thread(...)`.
- `⚠ Overrides` Treat [src/ed_route_services.py](src/ed_route_services.py) as a temporary legacy re-export module, but do not add new compatibility modules following that pattern.

## Datasources
- `➕ Extends` Implement datasource selection in [src/ed_datasource_factory.py](src/ed_datasource_factory.py).
- `➕ Extends` Resolve datasource type in the order explicit argument, environment variable, then TinyDB default.
- `➕ Extends` Support only `tinydb` and `redis` and fail fast on invalid values.
- `➕ Extends` Keep datasource creation lazy so backend modules are imported only when selected.
- `➕ Extends` Reuse the shared logger when constructing datasource instances.

## Redis
- `➕ Extends` Implement Redis behavior in [src/ed_redis.py](src/ed_redis.py).
- `➕ Extends` Use Redis as an optional persistence backend for cached system records, imports, exports, and lookup state.
- `➕ Extends` Resolve Redis settings from constructor arguments first, then environment variables.
- `➕ Extends` Require and validate `REDIS_URL` for Redis-backed operation.
- `➕ Extends` Namespace Redis keys by datasource or app name.
- `➕ Extends` Use `redis.asyncio` internally and expose sync-friendly methods by bridging async work back to sync callers.
- `➕ Extends` Bound connection growth with a configurable max-connections setting.
- `➕ Extends` Coordinate shutdown with close guards and `atexit` registration.
- `➕ Extends` Keep import/export behavior aligned with per-system JSON files.

## TinyDB
- `➕ Extends` Implement TinyDB behavior in [src/ed_tinydb.py](src/ed_tinydb.py).
- `➕ Extends` Use TinyDB as the local file-backed persistence backend for cached system records.
- `➕ Extends` Resolve the datasource path from constructor input first, then environment-backed defaults, and create parent directories before use.
- `➕ Extends` Use `SmartCacheTinyDB` with `SmartCacheTable` and `JSONStorage`.
- `➕ Extends` Wrap TinyDB access in `AIOTinyDB` and bridge back to sync-friendly methods in `EDTinyDB`.
- `➕ Extends` Maintain in-memory per-system and all-systems caches for hot paths.
- `➕ Extends` Serialize writes with locks.
- `➕ Extends` Keep import/export behavior aligned with per-system JSON files.

## EDGIS
- `➕ Extends` Implement EDGIS HTTP access in [src/ed_edgis.py](src/ed_edgis.py).
- `➕ Extends` Use `EDGis` as the only direct HTTP gateway for EDGIS lookups.
- `➕ Extends` Use `aiohttp` with a bounded total timeout.
- `➕ Extends` Bridge async HTTP work back to synchronous callers.
- `➕ Extends` Limit direct EDGIS calls to the coords and neighbors endpoints needed for cache misses and route expansion.
- `➕ Extends` Convert transport and timeout failures into logged `None` results at the gateway boundary.
- `➕ Extends` Inject EDGIS fetch functions into higher-level services instead of making ad hoc HTTP calls elsewhere.

## Documentation and Dependency Manifests
- `➕ Extends` Keep shared cross-project rules in [ARCHITECTURE.md](ARCHITECTURE.md), project-specific infrastructure rules here, and feature or business behavior in [BUSINESS.md](BUSINESS.md).
- `➕ Extends` Use [dev-requirements.txt](dev-requirements.txt) as this repository's development dependency manifest.
- `➕ Extends` Keep [dev-requirements.txt](dev-requirements.txt) alphabetically ordered.
- `➕ Extends` Install both [requirements.txt](requirements.txt) and [dev-requirements.txt](dev-requirements.txt) in development environments.
- `➕ Extends` Add new non-runtime dependencies to [dev-requirements.txt](dev-requirements.txt) by default.
- `➕ Extends` Keep a short descriptive comment above every dependency listed in [dev-requirements.txt](dev-requirements.txt).

## Script Documentation
- `➕ Extends` Keep a dedicated scripts section in [README.md](README.md) for files in `scripts/`.
- `➕ Extends` Update that section whenever a script is added, changed, or removed.
- `➕ Extends` Keep the authoritative script descriptions as comments inside each script.
- `⚠ Overrides` Generate the README scripts section from in-script comments via [scripts/generate_readme.py](scripts/generate_readme.py).
