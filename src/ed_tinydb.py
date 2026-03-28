import asyncio
import json
import os
import threading
from typing import Any, cast

from tinydb import Query, TinyDB
from tinydb.storages import JSONStorage
from tinydb_smartcache import SmartCacheTable

from ed_protocols import LoggingProtocol, SystemInfo
from constants import (
    default_init_dir,
    default_tinydb_name,
    json_extension,
    system_info_name_field,
    system_info_neighbors_field,
    tinydb_name_env,
    value_key,
)

"""TinyDB persistence helpers for cached system records."""


def main() -> None: ...


class SmartCacheTinyDB(TinyDB):
    table_class = SmartCacheTable


class AIOTinyDB:
    """Minimal async-compatible wrapper around TinyDB."""

    def __init__(self, path: str):
        self._path = path
        self._db: TinyDB | None = None

    async def __aenter__(self) -> "AIOTinyDB":
        self._db = SmartCacheTinyDB(self._path, storage=JSONStorage)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def _require_db(self) -> TinyDB:
        if self._db is None:
            raise RuntimeError("AIOTinyDB must be used within 'async with'")
        return self._db

    async def contains(self, cond: Any) -> bool:
        return self._require_db().contains(cond)

    async def insert(self, document: dict[str, Any]) -> int:
        return self._require_db().insert(document)

    async def get(self, cond: Any) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._require_db().get(cond))

    async def update(self, fields: dict[str, Any], cond: Any) -> list[int]:
        return self._require_db().update(fields, cond)

    async def all(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._require_db().all())


class EDTinyDB:
    @staticmethod
    def create(
        logging_utils: LoggingProtocol,
        datasource_name: str | None = None,
    ) -> "EDTinyDB":
        resolved_datasource_name = datasource_name
        if resolved_datasource_name is None:
            resolved_datasource_name = os.getenv(tinydb_name_env) or default_tinydb_name
        return EDTinyDB(
            resolved_datasource_name,
            logging_utils=logging_utils,
        )

    def __init__(self, datasource_name: str, logging_utils: LoggingProtocol):
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self.logger = logging_utils
        if datasource_name is None:
            raise ValueError("datasource_name of type str is required")
        else:
            self.datasource_name = datasource_name

        db_dir = os.path.dirname(self.datasource_name)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._write_lock = threading.Lock()
        self._cache_lock = threading.RLock()
        self._system_cache: dict[str, SystemInfo] = {}
        self._all_systems_cached = False

        self.logger.info("aiotinydb backend")

    def init_datasource(
        self,
        import_dir: str = default_init_dir,
    ) -> None:
        db_dir = os.path.dirname(self.datasource_name)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.import_datasource(import_dir)

    def import_datasource(self, import_dir: str) -> None:
        if not os.path.isdir(import_dir):
            raise FileNotFoundError(f"Import directory does not exist: {import_dir}")
        json_filenames = sorted(
            filename
            for filename in os.listdir(import_dir)
            if filename.endswith(json_extension)
        )
        self.logger.info(
            "Importing TinyDB datasource from {} JSON files in {}",
            len(json_filenames),
            import_dir,
        )
        for filename in json_filenames:
            json_path = os.path.join(import_dir, filename)
            with open(json_path, encoding="utf-8") as json_file:
                payload = json.load(json_file)

            file_records = payload if isinstance(payload, list) else [payload]
            for record in file_records:
                if isinstance(record, dict):
                    self.insert_system(record)

    def export_datasource(self, export_dir: str) -> None:
        os.makedirs(export_dir, exist_ok=True)
        systems = self.get_all_systems()
        for system in systems:
            system_name = system.get(system_info_name_field)
            if not isinstance(system_name, str) or not system_name:
                continue
            full_system = self.get_system(system_name)
            if full_system is None:
                continue
            output_file = os.path.join(
                export_dir,
                f"{self._safe_filename(system_name)}{json_extension}",
            )
            with open(output_file, "w", encoding="utf-8") as file_handle:
                json.dump(
                    full_system,
                    file_handle,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                file_handle.write("\n")

    def _safe_filename(self, system_name: str) -> str:
        return "".join(
            (
                character
                if character.isalnum() or character in (" ", "-", "_", ".")
                else "_"
            )
            for character in system_name
        ).strip()

    def _run_async(self, coro: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        output: dict[str, Any] = {}
        error: dict[str, BaseException] = {}

        def _worker() -> None:
            try:
                output[value_key] = asyncio.run(coro)
            except BaseException as exc:
                error[value_key] = exc

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        worker.join()

        if value_key in error:
            raise error[value_key]

        return output.get(value_key)

    def _cache_get(self, system_name: str) -> SystemInfo | None:
        with self._cache_lock:
            return self._system_cache.get(system_name)

    def _cache_set(self, system_name: str, system_info: SystemInfo) -> None:
        with self._cache_lock:
            self._system_cache[system_name] = system_info

    async def _insert_system_async(self, system_info: SystemInfo) -> bool:
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
                self._all_systems_cached = False

    async def _get_system_async(self, system_name: str) -> SystemInfo | None:
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
        with self._cache_lock:
            if self._all_systems_cached:
                return list(self._system_cache.values())
        async with AIOTinyDB(self.datasource_name) as db:
            systems = await db.all()
        typed_systems = [cast(SystemInfo, system) for system in systems]
        with self._cache_lock:
            self._system_cache = {
                system[system_info_name_field]: system
                for system in typed_systems
                if system_info_name_field in system
            }
            self._all_systems_cached = True
        return typed_systems

    def get_all_systems(self) -> list[SystemInfo]:
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
