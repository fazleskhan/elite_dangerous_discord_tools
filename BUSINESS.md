# Business Rules

This document captures the current behavior that the application enforces. It is derived from the codebase as of 2026-03-29.

## Routing
- `path` searches for a route between a source and destination system.
- The CLI `path` command requires `--initial`, `--destination`, and `--max_systems`.
- `--max_systems` must not be greater than `1000`.
- CLI route searches default to `min_distance=0` and `max_distance=10000` when those options are not supplied.
- Route progress messages are surfaced through the shared logger while the route search is running.
- When the CLI finds a route, it logs the route as a ` -> ` joined path.
- If no route is found, the CLI does not emit a special fallback route string; users see only the normal progress and execution-time logging for that command path.
- The Discord `path` command sends an immediate “this may take a while” message before the search runs.
- The Discord `path` command forwards progress updates back into the channel while the route search is running.
- When Discord finds a route, it sends the route as a ` → ` joined path followed by elapsed time.
- When Discord cannot find a route, it sends a “No Path found” message that includes the source, destination, and max system count.

## Route Search Behavior
- Route searches are executed through a breadth-first traversal over cached or fetched neighbor relationships.
- If the source and destination system names are identical, the route result is a single-item path containing that system.
- Route traversal stops when the visited-node count exceeds the requested maximum system count.
- Route traversal prunes nodes that move at least 5 percent farther away from the destination than the best distance seen so far in the current search.
- Route expansion ignores neighbors whose hop distance falls outside the requested `min_distance` and `max_distance` bounds.
- When neighbor payloads do not include a precomputed hop distance, the application computes that hop distance on demand.
- Route progress updates are throttled and are only emitted after at least 512 analyzed systems and at least 30 seconds since the last progress report.
- Path execution is offloaded to a worker thread so async callers such as Discord commands stay responsive while the traversal runs.

## Distance
- `calc_systems_distance` calculates Euclidean distance from cached or fetched system coordinates.
- The CLI distance command requires `--initial` and `--destination`.
- The Discord distance command returns a human-readable sentence containing both system names, the computed distance, and elapsed time.

## System Info And Cache Inspection
- `system_info` requires `--system_name`.
- The CLI `system_info` command logs the requested system name and then logs the returned payload.
- `all_loaded_systems` returns the currently cached system names.
- The Discord `system_info` command converts the fetched payload to text before sending it.
- Discord `system_info` responses that fit within 2000 characters are sent as a single message with elapsed time appended.
- Discord `system_info` responses longer than 2000 characters are split into 2000-character chunks, followed by a separate execution-time message.
- `bulk_load_cache` requires `--initial_systems` and `--max_nodes_visited`.
- `bulk_load_cache` trims whitespace around comma-separated seed names and ignores empty entries.
- The CLI bulk-load command reports how many systems were loaded from the cleaned seed list.
- The Discord bulk-load command announces the cleaned seed list before loading and reports the loaded-system count after completion.
- The Discord cache-dump command announces that cache inspection may take a while, sends cached system names in batches of 10, and finishes with the total count.
- The reusable Discord chunking helper defaults to batches of 5 items when a caller does not override the chunk size.

## Datasource Import And Export
- `init_datasource` initializes the configured datasource from the import directory.
- Both TinyDB and Redis import routines fail fast with `FileNotFoundError` when the import directory does not exist.
- Both TinyDB and Redis imports scan only files ending in the configured JSON extension.
- Import files may contain either a single JSON object or a JSON list; single objects are wrapped into a one-item list before processing.
- Import routines ignore non-dictionary records inside JSON payloads.
- `import_tinydb` imports per-system JSON files into TinyDB.
- `import_redis` imports per-system JSON files into Redis.
- `export_tinydb` exports TinyDB records into per-system JSON files.
- `export_redis` exports Redis records into per-system JSON files.
- Export routines create the target directory if it does not already exist.
- Export routines skip records with missing or empty system names.
- Export routines skip records whose full system payload cannot be reloaded from the backing store.
- Exported filenames are sanitized so unsupported characters are replaced with underscores.
- Exported JSON is pretty-printed, sorted by key, and terminated with a trailing newline.

## Cache And Persistence Behavior
- TinyDB and Redis both ignore insert requests for systems that do not have a non-empty `name` field.
- TinyDB avoids duplicate inserts by checking both its in-memory cache and the persisted store.
- TinyDB caches individual systems in memory after reads and inserts.
- TinyDB can satisfy synchronous callers even when already inside an event loop by executing async datastore work in a worker thread.
- TinyDB neighbor updates replace the stored neighbors list for the target system.
- TinyDB all-systems reads populate an in-memory cache that can be reused on later calls.
- Redis namespaces keys by datasource name so multiple app instances can share one Redis safely.
- Redis validates `REDIS_URL` and accepts only the `redis`, `rediss`, and `unix` schemes.
- Redis requires a host for `redis` and `rediss` URLs.
- Redis chooses a default max-connection count from the physical CPU count and never falls below `1`.
- Redis closes clients after each logical operation and supports both modern async close methods and legacy close methods.
- Redis and TinyDB both log which backend is active when the datasource object is created.

## Bulk Cache Load Behavior
- Bulk cache loading performs a frontier-by-frontier graph expansion starting from the user-provided seed systems.
- Seed systems are trimmed, blank seed names are ignored, and duplicate seed names are skipped.
- The bulk-load result preserves deterministic visit order in the order systems are first accepted into the visited set.
- Bulk loading returns early with an empty result when `max_nodes_visited` is zero or negative.
- Neighbor expansion is fetched in parallel through a thread pool sized from the detected physical CPU count, with a logical-core fallback when the physical count is unavailable.
- Bulk loading reuses neighbor payloads directly when they already include coordinate data and only performs a separate system-info lookup when a neighbor record is too incomplete for later expansion.
- Bulk-load progress updates are emitted only when the visited count reaches exact 512-system boundaries.

## Distance Service Behavior
- Distance calculations cache resolved coordinate triplets in memory and reuse them across later distance requests.
- If either requested system cannot be resolved to coordinates, the distance service raises `ValueError` naming every missing system in one message.

## EDGIS Webservice Interactions
- The project calls `https://edgis.elitedangereuse.fr/coords` to fetch system coordinate and metadata payloads by system name.
- The project sends the requested system name to the coords endpoint through the `q` query parameter.
- The project calls `https://edgis.elitedangereuse.fr/neighbors` to fetch neighboring systems around known coordinates.
- Neighbor lookups send the cached or fetched `x`, `y`, and `z` coordinate values as query parameters.
- The neighbors request intentionally omits a radius parameter and relies on the EDGIS service default radius behavior used by the current implementation.
- EDGIS requests use a 15-second total HTTP timeout.
- Successful EDGIS responses are consumed as JSON payloads and then passed into the cache and datasource flows for reuse.
- EDGIS transport failures and timeouts are logged and converted into missing-result behavior instead of being surfaced to users as raw HTTP exceptions.

## EDGis Cache Behavior
- Cache lookups are cache-through operations over the local datasource plus the EDGIS fetchers.
- On a system-info cache miss, the application fetches system info once, persists it to the datasource, and reuses it on later reads.
- On a neighbor cache miss, the application fetches neighbors from coordinates, persists them to the datasource, and reuses them on later reads.
- Cache hits and cache misses are logged distinctly for both system info and neighbors.
- Failed EDGIS lookups log warnings instead of raising for normal cache-miss behavior.

## Discord Bot
- The Discord bot exposes commands for ping, system info, route calculation, distance calculation, cache inspection, datasource initialization, and bulk cache loading.
- The default Discord command prefix is `!` when a caller does not inject a different prefix.
- The default Discord bot intents enable both message content and member access.
- The bot registers command wrappers against the underlying Discord bot so command callbacks use the signatures expected by `discord.ext.commands`.
- The bot accepts both synchronous and asynchronous route-service collaborators by resolving awaitable results at the call boundary.
- `ping` returns `Pong` with elapsed time in milliseconds.
- `run()` raises `RuntimeError` if the Discord token is not configured.
- The runner logs bot startup and re-raises unexpected failures so they keep their traceback.
