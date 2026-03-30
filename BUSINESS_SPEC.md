# Business Reconstruction Spec

This document is a reconstruction-grade specification for the user-visible, workflow-visible, and integration-visible behavior of the Elite Dangerous Discord Tools application. It defines what the rebuilt `src/` implementation must do.

Use this document together with [INFRASTRUCTURE_SPEC.md](INFRASTRUCTURE_SPEC.md). This file describes the required behavior. `INFRASTRUCTURE_SPEC.md` describes how to structure and wire the implementation.

## 1. Product Scope

The application provides:
- a synchronous CLI for route lookup, system inspection, datasource initialization, bulk cache loading, and distance calculation
- a Discord bot exposing equivalent operational capabilities
- utility commands for importing and exporting per-system JSON records
- storage through TinyDB or Redis
- cache-through lookups backed by the EDGIS service

## 2. CLI Command Contracts

### `ping`
- Returns `Pong`.

### `all_loaded_systems`
- Returns the currently loaded system names.

### `system_info`
- Requires `--system_name`.
- Logs the requested system name.
- Logs the returned system payload.

### `path`
- Requires `--initial`, `--destination`, and `--max_systems`.
- Rejects `--max_systems` values greater than `1000`.
- Defaults to `min_distance=0` and `max_distance=10000`.
- Emits progress through logging while the search runs.
- When a route exists, logs the route as a ` -> ` joined path.
- When no route exists, does not emit a special fallback route string in CLI output beyond normal progress and execution-time logging.

### `calc_systems_distance`
- Requires `--initial` and `--destination`.
- Logs the computed distance.

### `init_datasource`
- Initializes the active datasource from the supplied import directory.

### `bulk_load_cache`
- Requires `--initial_systems` and `--max_nodes_visited`.
- Trims comma-separated seed names.
- Ignores blank seed entries.
- Logs how many systems were loaded from the cleaned seed list.

## 3. Discord Command Contracts

### General
- The default command prefix is `!`.
- The bot must accept both synchronous and asynchronous route-service collaborators.

### `ping`
- Replies with `Pong` and elapsed milliseconds.

### `system_info`
- Converts the fetched payload to text before sending.
- If the rendered payload length is 2000 characters or less, sends it as one message with elapsed time appended.
- If the rendered payload is longer than 2000 characters, splits it into 2000-character chunks and then sends a separate execution-time message.

### `path`
- Sends an immediate acknowledgement that the operation may take a while.
- Sends progress updates into the channel while the route search runs.
- When a route exists, sends a ` → ` joined route plus elapsed time.
- When no route exists, sends a `No Path found` message containing source, destination, and max system count plus elapsed time.

### `calc_systems_distance`
- Sends both system names, the computed distance, and elapsed time in one sentence.

### `dump_system_cache_names`
- Announces that cache inspection may take time.
- Sends system names in batches of 10.
- Finishes by reporting the total number of systems in cache plus elapsed time.

### `init_datasource`
- Reports the import directory used and elapsed time.

### `bulk_load_cache`
- Trims comma-separated seeds and ignores blanks.
- Announces the cleaned seed list before loading.
- Reports the total loaded-system count after completion.

### `run`
- Raises `RuntimeError` if the Discord token is missing.

## 4. Route Search Rules

- Route search uses breadth-first traversal over neighbor relationships.
- Neighbor relationships may come from cache or from EDGIS-backed cache misses.
- If the source and destination are identical, the route is a one-item list containing that system.
- Route search stops when the analyzed node count exceeds the requested maximum.
- Route search ignores neighbors whose hop distance falls outside the requested min and max bounds.
- If a neighbor payload omits hop distance, the application computes that distance on demand.
- Route search prunes nodes that are at least 5 percent farther from the destination than the best distance seen so far in the current search.
- Route progress updates are throttled and emitted only when both conditions are true:
  - at least 512 systems have been analyzed
  - at least 30 seconds have elapsed since the previous route progress update

## 5. Distance Rules

- Distance is Euclidean distance computed from system coordinates.
- Coordinate triplets are cached in memory for reuse across later distance requests.
- If either requested system cannot be resolved to coordinates, the distance service raises `ValueError`.
- The error message must name every missing system in one message.

## 6. Cache Rules

### System Info Cache
- System-info lookups are cache-through reads.
- On a cache hit, the local datasource result is reused.
- On a cache miss, the application fetches system info from EDGIS once, stores it, and reuses it on later reads.

### Neighbor Cache
- Neighbor lookups are cache-through reads.
- On a cache hit, stored neighbors are reused.
- On a cache miss, the application fetches neighbors from EDGIS using the system coordinates, stores them, and reuses them on later reads.

### Cache Logging
- Cache hits and misses are logged distinctly for both system info and neighbors.
- Normal cache-miss fetch failures log warnings instead of raising user-visible transport exceptions.

## 7. Bulk Cache Load Rules

- Bulk cache loading begins from the user-provided seed systems.
- Seed names are trimmed.
- Blank seed names are ignored.
- Duplicate seed names are skipped.
- The result preserves deterministic visit order based on first acceptance into the visited set.
- If `max_nodes_visited` is zero or negative, the result is an empty list.
- Neighbor expansion uses a worker pool sized from physical CPU count, with a logical-core fallback.
- When a neighbor payload already includes coordinate data, it can be reused directly for future expansion.
- When a neighbor payload is too incomplete, the application performs an additional system-info lookup before queuing that neighbor for future expansion.
- Bulk-load progress updates are emitted only at exact 512-system boundaries.

## 8. Datasource Selection Rules

- The active datasource may be TinyDB or Redis.
- If a caller injects a datasource explicitly, that datasource is used.
- If a caller does not inject a datasource, backend selection follows `DATASOURCE_TYPE`.
- Datasource type resolution order is:
  1. explicit argument
  2. environment variable
  3. TinyDB default
- Only `tinydb` and `redis` are valid datasource types.
- Invalid datasource types must fail fast.

## 9. Import And Export Rules

### Import
- `init_datasource` loads seed data into the active datasource.
- Import fails with `FileNotFoundError` when the import directory does not exist.
- Import scans only files ending with the configured JSON extension.
- An import file may contain:
  - one JSON object
  - a JSON list of objects
- A single JSON object is treated as a one-item list.
- Non-dictionary records inside JSON payloads are ignored.

### Export
- Export creates the target directory if it does not already exist.
- Export skips records with missing or empty system names.
- Export skips records whose full payload cannot be reloaded from the backing store.
- Export sanitizes filenames by replacing unsupported characters with underscores.
- Export writes pretty-printed JSON.
- Export sorts JSON keys.
- Export writes a trailing newline at end of file.

## 10. TinyDB Rules

- TinyDB is the local file-backed persistence option.
- TinyDB ignores insert requests for records that do not contain a non-empty `name`.
- TinyDB avoids duplicate inserts by checking both in-memory cache and persisted state.
- TinyDB caches individual system records after reads and inserts.
- TinyDB caches full-system scans for reuse on later calls.
- TinyDB can still satisfy synchronous callers when already inside an event loop by moving async datastore work to a worker thread.

## 11. Redis Rules

- Redis is the optional network-backed persistence option.
- Redis namespaces keys by datasource name so multiple app instances can share one Redis safely.
- Redis requires a valid `REDIS_URL`.
- Valid Redis URL schemes are:
  - `redis`
  - `rediss`
  - `unix`
- `redis` and `rediss` URLs require a host.
- Redis chooses a default max-connection count from physical CPU count and never goes below `1`.
- Redis closes its short-lived clients after each logical operation.

## 12. EDGIS Rules

- The application uses `https://edgis.elitedangereuse.fr/coords` to fetch system metadata and coordinates.
- The coords request sends the requested system name through the `q` query parameter.
- The application uses `https://edgis.elitedangereuse.fr/neighbors` to fetch nearby systems from coordinates.
- The neighbors request sends `x`, `y`, and `z` query parameters.
- The neighbors request relies on the EDGIS service default radius behavior and does not set a radius explicitly.
- EDGIS requests use a 15-second total timeout.
- Transport failures and timeouts are logged.
- Transport failures and timeouts become missing-result behavior rather than raw HTTP exceptions shown to users.

## 13. Logging-Visible Behavior

- CLI entrypoints log parsed parameters at `info` level.
- CLI handled errors are logged once at the CLI boundary and exit without traceback.
- Unexpected failures preserve traceback.
- Route progress and bulk-load progress are surfaced through logging.
- Discord progress updates are logged and echoed into the channel when applicable.

## 14. Output-Visible Formatting Rules

- CLI route output uses ` -> ` between hop names.
- Discord route output uses ` → ` between hop names.
- Discord `system_info` long responses chunk at 2000 characters.
- Discord cache-name dumps use batches of 10 names per message.
- Shared chunking helpers default to batches of 5 items when no size override is supplied.

## 15. Reconstruction Acceptance Criteria

A rebuilt implementation satisfies this business spec only if all of the following are true:
- every CLI command above behaves as specified
- every Discord command above behaves as specified
- route search, distance, cache, import, export, TinyDB, Redis, and EDGIS behavior all match the rules above
- user-visible errors and outputs match the current behavior contracts
