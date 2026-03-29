# Project-Specific Architecture Companion

Use this file with [ARCHITECTURE.md](ARCHITECTURE.md) as the repository-specific infrastructure prompt for Elite Dangerous Discord Tools.

## Purpose
- Regenerate this repository with the shared contract from `ARCHITECTURE.md` plus the project-specific constraints below.
- Treat these entries as concise implementation prompts for local infrastructure code.
- If a prompt here conflicts with `ARCHITECTURE.md`, this file wins for this repository.

## Entry Points
- Keep [src/main.py](src/main.py) as the synchronous CLI entry point.
- Keep [src/ed_discord_bot.py](src/ed_discord_bot.py) as the Discord-triggered entry point module.
- When entry points change, regenerate matching per-entrypoint sequence diagrams.

## Diagram Layout
- Put CLI entrypoint sequence sources under `docs/diagrams/cli/`.
- Put Discord entrypoint sequence sources under `docs/diagrams/discord/`.
- Put shared structure diagrams under `docs/diagrams/`.
- Remove stale diagrams when a clearer authoritative source replaces them.

## Config Watching
- Implement logging config watching in [src/app_logging.py](src/app_logging.py).
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
- Resolve the datasource path from constructor input first, then environment-backed defaults, and create parent directories before use.
- Use `SmartCacheTinyDB` with `SmartCacheTable` and `JSONStorage`.
- Wrap TinyDB access in `AIOTinyDB` for async-compatible usage, then bridge back to sync-friendly methods in `EDTinyDB`.
- Maintain in-memory per-system caching and all-systems caching for hot lookup paths.
- Serialize writes with locks to protect single-process TinyDB state.
- Keep import/export behavior aligned with per-system JSON files.

## EDGIS Webservice Integration
- Implement EDGIS HTTP access in [src/edgis.py](src/edgis.py).
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
