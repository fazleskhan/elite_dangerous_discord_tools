import os
import threading
from pathlib import Path
from typing import Any, cast

from ed_datasource_json_io import (
    export_json_records,
    import_json_records,
    safe_filename,
)
from tinydb import Query, TinyDB
from tinydb.storages import JSONStorage
from tinydb_smartcache import SmartCacheTable

from ed_protocols import LoggingProtocol, SystemInfo
from ed_sync_async_bridge import run_async_from_sync
from ed_constants import (
    default_init_dir,
    default_tinydb_name,
    json_extension,
    system_info_name_field,
    system_info_neighbors_field,
    tinydb_name_env,
    value_key,
)

"""TinyDB persistence helpers for cached system records."""


class SmartCacheTinyDB(TinyDB):
    """TinyDB variant that uses the smart-cache table implementation.

    The subclass exists purely to swap TinyDB's default table class for the
    smart-cache table so repeated table reads can benefit from that caching
    behavior without changing call sites elsewhere in the project.
    """

    table_class = SmartCacheTable


class AIOTinyDB:
    """Minimal async-compatible wrapper around TinyDB."""

    def __init__(self, path: str | Path):
        """Store the TinyDB path and defer opening until context entry.

        The wrapper mirrors async resource life cycles even though TinyDB itself
        is synchronous, which lets higher-level code use one async style around
        database operations.
        """
        self._path = str(path)
        self._db: TinyDB | None = None

    async def __aenter__(self) -> "AIOTinyDB":
        """Open the TinyDB file and return the wrapper instance.

        Entering the async context creates the underlying TinyDB instance so the
        wrapper can satisfy subsequent async-style database operations.
        """
        self._db = SmartCacheTinyDB(self._path, storage=JSONStorage)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        """Close the TinyDB file when leaving the async context.

        The wrapper cleans up the underlying TinyDB object and resets its stored
        reference so later operations cannot accidentally reuse a closed handle.
        """
        if self._db is not None:
            self._db.close()
            self._db = None

    def _require_db(self) -> TinyDB:
        """Return the active TinyDB instance or raise when unopened.

        Async wrapper methods call this guard to ensure they only operate while
        the wrapper is inside an `async with` block.
        """
        if self._db is None:
            raise RuntimeError("AIOTinyDB must be used within 'async with'")
        return self._db

    async def contains(self, cond: Any) -> bool:
        """Return whether any document matches the provided TinyDB condition.

        The method forwards to the underlying TinyDB instance while preserving
        the async-compatible wrapper surface used by higher layers.
        """
        return self._require_db().contains(cond)

    async def insert(self, document: dict[str, Any]) -> int:
        """Insert one document and return its TinyDB document id.

        The wrapper delegates directly to TinyDB while keeping the surrounding
        API consistent with the async context manager.
        """
        return self._require_db().insert(document)

    async def get(self, cond: Any) -> dict[str, Any] | None:
        """Return the first document that matches the provided condition.

        The method forwards the lookup to TinyDB and normalizes the result into
        the dictionary-or-`None` shape used by the rest of the project.
        """
        return cast(dict[str, Any] | None, self._require_db().get(cond))

    async def update(self, fields: dict[str, Any], cond: Any) -> list[int]:
        """Update matching documents and return the affected document ids.

        The wrapper simply exposes TinyDB's update result through the async
        surface used by the datasource implementation.
        """
        return self._require_db().update(fields, cond)

    async def all(self) -> list[dict[str, Any]]:
        """Return every document stored in the TinyDB file.

        Higher-level code uses this method for exports and cache rebuilding
        while keeping all DB interactions inside the wrapper.
        """
        return cast(list[dict[str, Any]], self._require_db().all())


class EDTinyDB:
    """TinyDB-backed datasource for cached system records.

    The datasource stores system payloads in a local TinyDB file, bridges its
    synchronous operations into async-compatible helpers where needed, and keeps
    a small in-memory cache for faster repeat reads.
    """

    @staticmethod
    def create(
        logger: LoggingProtocol,
        datasource_name: str | None = None,
    ) -> "EDTinyDB":
        """Build a TinyDB datasource using defaults when no name is supplied.

        The factory resolves the database filename from explicit input,
        environment variables, or the project default before constructing the
        datasource instance.
        """
        resolved_datasource_name = datasource_name
        if resolved_datasource_name is None:
            resolved_datasource_name = os.getenv(tinydb_name_env) or default_tinydb_name
        return EDTinyDB(
            resolved_datasource_name,
            logger=logger,
        )

    def __init__(self, datasource_name: str, logger: LoggingProtocol):
        """Initialize TinyDB paths, locks, and in-memory caches.

        The constructor validates the logger and datasource name, prepares the
        parent directory for the TinyDB file, and sets up the caches and locks
        used by later reads and writes.
        """
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self.logger = logger
        if datasource_name is None:
            raise ValueError("datasource_name of type str is required")
        self.datasource_name = datasource_name

        if db_dir := Path(self.datasource_name).parent:
            db_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.Lock()
        self._cache_lock = threading.RLock()
        self._system_cache: dict[str, SystemInfo] = {}
        self._all_systems_cached = False

        self.logger.info("aiotinydb backend")

    def init_datasource(
        self,
        import_dir: str | Path = default_init_dir,
    ) -> None:
        """Initialize the TinyDB datasource from a seed directory.

        The method ensures the TinyDB directory exists and then delegates the
        actual JSON import work to `import_datasource`.
        """
        if db_dir := Path(self.datasource_name).parent:
            db_dir.mkdir(parents=True, exist_ok=True)
        self.import_datasource(import_dir)

    def import_datasource(self, import_dir: str | Path) -> None:
        """Import per-system JSON files into TinyDB.

        The method delegates directory walking and JSON decoding to the shared
        import helper and inserts each decoded record through this datasource.
        """
        import_json_records(
            import_dir=import_dir,
            json_extension=json_extension,
            logger=self.logger,
            log_message="Importing TinyDB datasource from {} JSON files in {}",
            insert_record=self.insert_system,
        )

    def export_datasource(self, export_dir: str) -> None:
        """Export all stored systems from TinyDB into JSON files.

        The method delegates the filesystem work to the shared export helper and
        resolves each listed system through this datasource's lookup method.
        """
        export_json_records(
            export_dir=export_dir,
            json_extension=json_extension,
            systems=self.get_all_systems(),
            system_name_field=system_info_name_field,
            get_full_system=self.get_system,
        )

    def _safe_filename(self, system_name: str) -> str:
        """Return a filesystem-safe filename derived from a system name.

        This thin wrapper preserves the datasource's older helper surface while
        delegating the actual sanitization to the shared JSON I/O helper.
        """
        return safe_filename(system_name)

    def _run_async(self, coro: Any) -> Any:
        """Execute a coroutine from this synchronous datasource.

        TinyDB entrypoints are synchronous, so this helper bridges internal
        async-style helpers back into the synchronous public API.
        """
        return run_async_from_sync(coro, value_key=value_key)

    def _cache_get(self, system_name: str) -> SystemInfo | None:
        """Return a cached system payload if it is already in memory.

        The helper reads the per-system cache under a lock so repeated lookups
        can avoid hitting TinyDB when the record is already warm.
        """
        with self._cache_lock:
            return self._system_cache.get(system_name)

    def _cache_set(self, system_name: str, system_info: SystemInfo) -> None:
        """Store a system payload in the in-memory cache.

        The helper centralizes cache writes under the shared lock so other
        methods can update cached system state consistently.
        """
        with self._cache_lock:
            self._system_cache[system_name] = system_info

    async def _insert_system_async(self, system_info: SystemInfo) -> bool:
        """Insert a system record into TinyDB when it is not already present.

        The helper performs the actual TinyDB insert inside the async wrapper
        context and returns whether a new record was written.
        """
        System = Query()
        system_name = system_info[system_info_name_field]
        async with AIOTinyDB(self.datasource_name) as db:
            if not await db.contains(System.name == system_name):
                inserted_id = await db.insert(system_info)
                self.logger.debug(
                    "Inserted system={} doc_id={}", system_name, inserted_id
                )
                return True
            else:
                self.logger.debug("Skipped existing system={}", system_name)
                return False

    def insert_system(self, system_info: SystemInfo) -> None:
        """Persist one system record and update local caches.

        The method validates the system name, avoids duplicate cache work, and
        performs the TinyDB insert under a write lock before updating in-memory
        cache state.
        """
        system_name = system_info.get(system_info_name_field)
        if not isinstance(system_name, str) or not system_name:
            return
        if self._cache_get(system_name) is not None:
            return
        with self._write_lock:
            inserted = self._run_async(self._insert_system_async(system_info))
        if inserted:
            self._cache_set(system_name, system_info)
            with self._cache_lock:
                # A single insert invalidates the cached all-systems snapshot.
                self._all_systems_cached = False

    async def _get_system_async(self, system_name: str) -> SystemInfo | None:
        """Return one system payload from TinyDB, populating the memory cache.

        The helper checks the in-memory cache first and only queries TinyDB on a
        miss, caching any successfully loaded payload for future use.
        """
        cached = self._cache_get(system_name)
        if cached is not None:
            return cached
        System = Query()
        async with AIOTinyDB(self.datasource_name) as db:
            system = await db.get(System.name == system_name)
        if isinstance(system, dict):
            self._cache_set(system_name, system)
            return cast(SystemInfo, system)
        return None

    def get_system(self, system_name: str) -> SystemInfo | None:
        """Return one system payload, shielding callers from backend errors.

        The synchronous wrapper checks the in-memory cache, bridges the async
        TinyDB lookup when needed, and logs then returns `None` on unexpected
        backend failures.
        """
        cached = self._cache_get(system_name)
        if cached is not None:
            return cached
        try:
            system = cast(
                SystemInfo | None, self._run_async(self._get_system_async(system_name))
            )
        except Exception:
            self.logger.exception("Lookup failed for system={}", system_name)
            return None
        if isinstance(system, dict):
            self._cache_set(system_name, system)
            return system
        return None

    async def _get_all_systems_async(self) -> list[SystemInfo]:
        """Return all stored systems and refresh the in-memory caches.

        The helper reuses the cached all-systems snapshot when valid, otherwise
        loads every record from TinyDB and rebuilds the per-system cache from
        that authoritative scan.
        """
        with self._cache_lock:
            if self._all_systems_cached:
                return list(self._system_cache.values())
        async with AIOTinyDB(self.datasource_name) as db:
            systems = await db.all()
        typed_systems = [cast(SystemInfo, system) for system in systems]
        with self._cache_lock:
            # Rebuild the per-system cache from the authoritative table scan so
            # later single-item lookups can hit memory instead of disk.
            self._system_cache = {
                system[system_info_name_field]: system
                for system in typed_systems
                if system_info_name_field in system
            }
            self._all_systems_cached = True
        return typed_systems

    def get_all_systems(self) -> list[SystemInfo]:
        """Return all stored systems through the synchronous datasource API.

        The method reuses the cached all-systems snapshot when possible and
        otherwise bridges the async TinyDB scan into the synchronous caller
        interface.
        """
        with self._cache_lock:
            if self._all_systems_cached:
                return list(self._system_cache.values())
        systems = cast(list[SystemInfo], self._run_async(self._get_all_systems_async()))
        with self._cache_lock:
            self._system_cache = {
                system[system_info_name_field]: system
                for system in systems
                if system_info_name_field in system
            }
            self._all_systems_cached = True
        return systems

    async def _add_neighbors_async(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> int:
        """Merge new neighbor records into one stored system payload.

        The helper deduplicates neighbors by system name, updates the TinyDB
        record, refreshes the in-memory cache, and returns the number of
        updated rows reported by TinyDB.
        """
        System = Query()
        system_name = system_info[system_info_name_field]
        current_neighbors = list(system_info.get(system_info_neighbors_field, []))
        current_neighbor_names = {
            neighbor[system_info_name_field]
            for neighbor in current_neighbors
            if isinstance(neighbor, dict) and system_info_name_field in neighbor
        }
        merged_neighbors = current_neighbors + [
            neighbor
            for neighbor in new_neighbors
            if neighbor[system_info_name_field] not in current_neighbor_names
        ]
        async with AIOTinyDB(self.datasource_name) as db:
            updated_rows = await db.update(
                {system_info_neighbors_field: merged_neighbors},
                System.name == system_name,
            )
        updated_system = dict(system_info)
        updated_system[system_info_neighbors_field] = merged_neighbors
        self._cache_set(system_name, updated_system)
        return len(updated_rows)

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None:
        """Persist neighbor data for a system through the synchronous API.

        The method performs the underlying update under a write lock and logs
        the resulting update count for the affected system.
        """
        with self._write_lock:
            updated_rows = self._run_async(
                self._add_neighbors_async(system_info, new_neighbors)
            )
        system_name = system_info.get(system_info_name_field)
        if isinstance(system_name, str):
            self.logger.debug(
                "Updated neighbors for system={} updated_rows={}",
                system_name,
                updated_rows or 1,
            )
