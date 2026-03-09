import asyncio
import json
import os
import threading
from typing import Any

from loguru import logger
from tinydb import Query

import constants
from aiotinydb import AIOTinyDB

"""TinyDB persistence helpers for cached system records."""

SystemInfo = dict[str, Any]


def main() -> None: ...


class EDTinyDB:
    @staticmethod
    def create(
        datasource_name: str | None = None,
        logging_utils: Any = None,
    ) -> "EDTinyDB":
        # Keep local default under ./data unless caller/env overrides it.
        return EDTinyDB(
            datasource_name or os.getenv("TINYDB_NAME", "./data/ed_route.db")
        )

    def __init__(self, datasource_name: str):
        self.datasource_name = datasource_name
        db_dir = os.path.dirname(self.datasource_name)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        # Serialize write operations to avoid concurrent TinyDB write races.
        self._write_lock = threading.Lock()
        # Cache hot system lookups to avoid repeated TinyDB file scans.
        self._cache_lock = threading.RLock()
        self._system_cache: dict[str, SystemInfo] = {}
        self._all_systems_cached = False
        self.logger = logger
        self.logger.info("DB backend: aiotinydb")

    # Synchronous helper used by import scripts and CLI commands.
    def init_datasource(
        self,
        import_dir: str = "./init",
    ) -> None:
        db_dir = os.path.dirname(self.datasource_name)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.import_datasource(import_dir)

    # Import/export entrypoints are sync by design for CLI/script usage.
    def import_datasource(self, import_dir: str) -> None:
        if not os.path.isdir(import_dir):
            raise FileNotFoundError(f"Import directory does not exist: {import_dir}")
        # Deterministic order keeps imports reproducible across runs.
        json_filenames = sorted(
            filename
            for filename in os.listdir(import_dir)
            if filename.endswith(".json")
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

    # Import/export entrypoints are sync by design for CLI/script usage.
    def export_datasource(self, export_dir: str) -> None:
        os.makedirs(export_dir, exist_ok=True)
        systems = self.get_all_systems()
        for system in systems:
            system_name = system.get(constants.system_info_name_field)
            if not isinstance(system_name, str) or not system_name:
                continue
            full_system = self.get_system(system_name)
            if full_system is None:
                continue
            output_file = os.path.join(
                export_dir, f"{self._safe_filename(system_name)}.json"
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
        # If we're already inside an event loop, execute the coroutine in a
        # helper thread so sync callers can still block for the result.
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        output: dict[str, Any] = {}
        error: dict[str, BaseException] = {}

        def _worker() -> None:
            try:
                output["value"] = asyncio.run(coro)
            except BaseException as exc:
                error["value"] = exc

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        worker.join()

        if "value" in error:
            raise error["value"]

        return output.get("value")

    def _cache_get(self, system_name: str) -> SystemInfo | None:
        with self._cache_lock:
            return self._system_cache.get(system_name)

    def _cache_set(self, system_name: str, system_info: SystemInfo) -> None:
        with self._cache_lock:
            self._system_cache[system_name] = system_info

    async def _insert_system_async(self, system_info: SystemInfo) -> bool:
        System = Query()
        system_name = system_info[constants.system_info_name_field]
        async with AIOTinyDB(self.datasource_name) as db:
            if not await db.contains(System.name == system_name):
                inserted_id = await db.insert(system_info)
                self.logger.debug(
                    "Inserted system={} doc_id={}", system_name, inserted_id
                )
                return True
            else:
                self.logger.debug(
                    "Skipped duplicate system insert for system={}", system_name
                )
                return False

    async def _get_system_async(self, system_name: str) -> SystemInfo | None:
        System = Query()
        async with AIOTinyDB(self.datasource_name) as db:
            if not await db.contains(System.name == system_name):
                self.logger.debug("Lookup system={} found=False", system_name)
                return None
            result = await db.get(System.name == system_name)
            self.logger.debug(
                "Lookup system={} found={}", system_name, result is not None
            )
            return result

    async def _add_neighbors_async(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None:
        System = Query()
        system_name = system_info[constants.system_info_name_field]
        async with AIOTinyDB(self.datasource_name) as db:
            updated = await db.update(
                {constants.system_info_neighbors_field: new_neighbors},
                System.name == system_name,
            )
            self.logger.debug(
                "Updated neighbors for system={} updated_rows={}",
                system_name,
                len(updated),
            )

    async def _get_all_systems_async(self) -> list[SystemInfo]:
        async with AIOTinyDB(self.datasource_name) as db:
            systems = await db.all()
            self.logger.debug("Loaded all systems count={}", len(systems))
            return systems

    def insert_system(self, system_info: SystemInfo) -> None:
        system_name = system_info.get(constants.system_info_name_field)
        if not isinstance(system_name, str):
            return
        if self._cache_get(system_name) is not None:
            return
        with self._write_lock:
            inserted = self._run_async(self._insert_system_async(system_info))
        if inserted:
            self._cache_set(system_name, system_info)

    def get_system(self, system_name: str) -> SystemInfo | None:
        cached = self._cache_get(system_name)
        if cached is not None:
            return cached
        try:
            result = self._run_async(self._get_system_async(system_name))
            if isinstance(result, dict):
                self._cache_set(system_name, result)
            return result
        except Exception:
            self.logger.exception("Lookup failed for system={}", system_name)
            return None

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None:
        with self._write_lock:
            self._run_async(self._add_neighbors_async(system_info, new_neighbors))
        system_name = system_info.get(constants.system_info_name_field)
        if isinstance(system_name, str):
            updated_info = dict(system_info)
            updated_info[constants.system_info_neighbors_field] = new_neighbors
            self._cache_set(system_name, updated_info)

    def get_all_systems(self) -> list[SystemInfo]:
        with self._cache_lock:
            if self._all_systems_cached:
                return list(self._system_cache.values())
        systems = self._run_async(self._get_all_systems_async())
        with self._cache_lock:
            for system_info in systems:
                system_name = system_info.get(constants.system_info_name_field)
                if isinstance(system_name, str):
                    self._system_cache[system_name] = system_info
            self._all_systems_cached = True
        return systems


if __name__ == "__main__":
    main()
