# Business Rules

This document captures the current business-specific behavior enforced by the application. It is derived from the codebase as of 2026-03-30.

## CLI Commands
- `ping` returns `Pong`.
- `all_loaded_systems` returns the currently loaded system names.
- `system_info` requires `--system_name` and logs the requested name plus the returned payload.
- `path` requires `--initial`, `--destination`, and `--max_systems`.
- `path` rejects `--max_systems` values greater than `1000`.
- `path` defaults to `min_distance=0` and `max_distance=10000`.
- `calc_systems_distance` requires `--initial` and `--destination`.
- `init_datasource` initializes the configured datasource from the supplied import directory.
- `bulk_load_cache` requires `--initial_systems` and `--max_nodes_visited`.

## Discord Commands
- The default Discord command prefix is `!`.
- `ping` replies with `Pong` and elapsed milliseconds.
- `system_info` sends one message when the rendered payload fits within 2000 characters.
- `system_info` splits longer rendered payloads into 2000-character chunks and then sends execution time separately.
- `path` sends an immediate “this may take a while” acknowledgement before route calculation starts.
- `path` sends progress updates while the search runs.
- `path` returns either a `→`-joined route or a `No Path found` message with elapsed time.
- `calc_systems_distance` sends both system names, the computed distance, and elapsed time.
- `dump_system_cache_names` announces that cache inspection may take time, sends system names in batches of 10, and then reports the total count.
- `init_datasource` reports the import directory used and the elapsed time.
- `bulk_load_cache` trims comma-separated seed names, ignores blanks, announces the cleaned seed list, and reports the loaded-system count.
- `run()` fails with `RuntimeError` when the Discord token is missing.

## Route Search
- Route search uses breadth-first traversal over cached or fetched neighbor relationships.
- If source and destination are identical, the route is a single-item path containing that system.
- Route search stops when the analyzed node count exceeds the requested maximum.
- Route search ignores hops whose distance falls outside the requested min and max bounds.
- Route search prunes nodes that move at least 5 percent farther from the destination than the best distance seen so far in the current search.
- When a neighbor payload does not include hop distance, the application computes that distance on demand.
- Route progress updates are emitted only after at least 512 analyzed systems and at least 30 seconds since the previous report.

## Distance
- Distance is Euclidean distance computed from system coordinates.
- Distance calculations cache resolved coordinate triplets in memory for reuse.
- If either system cannot be resolved to coordinates, the distance service raises `ValueError` naming every missing system.

## Cache And Bulk Loading
- System-info lookups are cache-through reads backed by the local datasource plus EDGIS fetchers.
- On a system-info cache miss, the application fetches the system once, stores it, and reuses it on later reads.
- On a neighbor cache miss, the application fetches neighbors once, stores them, and reuses them on later reads.
- Bulk cache loading trims seed names, ignores blanks, and skips duplicate seeds.
- Bulk cache loading returns an empty result when `max_nodes_visited` is zero or negative.
- Bulk cache loading preserves deterministic visit order based on first acceptance into the visited set.
- Bulk cache loading fetches frontier neighbors in parallel using a worker pool sized from physical CPU count, with a logical-core fallback.
- Bulk cache loading emits progress updates only at exact 512-system boundaries.

## Datasource Import And Export
- The active datasource can be TinyDB or Redis.
- `init_datasource` loads seed data into the active datasource.
- Import fails with `FileNotFoundError` when the import directory does not exist.
- Import scans only files with the configured JSON extension.
- Import accepts either a single JSON object or a JSON list per file.
- Import ignores non-dictionary records inside JSON payloads.
- Export creates the target directory when needed.
- Export skips records with missing or empty system names.
- Export skips records whose full payload cannot be reloaded from the backing store.
- Export sanitizes filenames by replacing unsupported characters with underscores.
- Export writes pretty-printed, sorted JSON ending with a trailing newline.

## TinyDB Behavior
- TinyDB is the local file-backed persistence option.
- TinyDB ignores insert requests for systems without a non-empty `name`.
- TinyDB avoids duplicate inserts by checking both its in-memory cache and persisted store.
- TinyDB caches individual systems after reads and inserts.
- TinyDB caches full-system scans for reuse on later calls.
- TinyDB can satisfy synchronous callers even when already inside an event loop by running async datastore work in a worker thread.

## Redis Behavior
- Redis is the optional network-backed persistence option.
- Redis namespaces keys by datasource name so multiple app instances can share one Redis safely.
- Redis requires a valid `REDIS_URL` using the `redis`, `rediss`, or `unix` scheme.
- Redis requires a host for `redis` and `rediss` URLs.
- Redis chooses a default max-connection count from the physical CPU count and never goes below `1`.
- Redis closes its short-lived clients after each logical operation.

## EDGIS Integration
- The project calls `https://edgis.elitedangereuse.fr/coords` for system metadata and coordinates.
- The coords request sends the system name through the `q` query parameter.
- The project calls `https://edgis.elitedangereuse.fr/neighbors` for nearby systems around known coordinates.
- The neighbors request sends `x`, `y`, and `z` query parameters and relies on the service's default radius behavior.
- EDGIS requests use a 15-second total timeout.
- Transport failures and timeouts are logged and converted into missing-result behavior instead of surfacing raw HTTP errors to users.
