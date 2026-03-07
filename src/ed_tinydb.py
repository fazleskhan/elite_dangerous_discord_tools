import asyncio
import os
import shutil
import threading
from typing import Any, Callable

from loguru import logger
from tinydb import Query

import constants
from aiotinydb import AIOTinyDB

"""TinyDB persistence helpers for cached system records."""

# https://www.tutorialspoint.com/tinydb/index.htm

SystemInfo = dict[str, Any]


def main() -> None: ...


class EDTinyDB:
    def __init__(self, database_name: str):
        self._database_name = database_name
        # Serialize write operations to avoid concurrent TinyDB write races.
        self._write_lock = threading.Lock()
        self.logger = logger
        self.logger.info("DB backend: aiotinydb")

    def _resolve_preload_source_path(
        self,
        script_file: str,
        preinit_db_filename: str,
        file_exists: Callable[[str], bool],
    ) -> str:
        if os.path.isabs(preinit_db_filename):
            return preinit_db_filename

        script_dir = os.path.dirname(os.path.realpath(script_file))
        repo_root = os.path.normpath(os.path.join(script_dir, ".."))
        repo_source_path = os.path.join(repo_root, preinit_db_filename)
        # Prefer repo-relative preload location (e.g. init/edgis_bulk_load.db).
        if file_exists(repo_source_path):
            return repo_source_path

        return os.path.join(script_dir, preinit_db_filename)

    def init_db(
        self,
        script_file: str,
        preinit_db_filename: str = constants.pre_initiazlied_db_filename,
        file_exists: Callable[[str], bool] = os.path.exists,
        copy_file: Callable[[str, str], str] = shutil.copy,
    ) -> None:
        # First run: copy preloaded DB to the configured writable target.
        if file_exists(self._database_name):
            self.logger.debug("DB already exists at {}", self._database_name)
            return
        db_dir = os.path.dirname(self._database_name)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        source_path = self._resolve_preload_source_path(
            script_file, preinit_db_filename, file_exists
        )
        self.logger.info(
            "Copying preloaded DB from {} to {}", source_path, self._database_name
        )
        copy_file(source_path, self._database_name)

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

    async def _insert_system_async(self, system_info: SystemInfo) -> None:
        System = Query()
        system_name = system_info[constants.system_info_name_field]
        async with AIOTinyDB(self._database_name) as db:
            if not await db.contains(System.name == system_name):
                inserted_id = await db.insert(system_info)
                self.logger.debug(
                    "Inserted system={} doc_id={}", system_name, inserted_id
                )
            self.logger.debug(
                "Skipped duplicate system insert for system={}", system_name
            )

    async def _get_system_async(self, system_name: str) -> SystemInfo | None:
        System = Query()
        async with AIOTinyDB(self._database_name) as db:
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
        async with AIOTinyDB(self._database_name) as db:
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
        async with AIOTinyDB(self._database_name) as db:
            systems = await db.all()
            self.logger.debug("Loaded all systems count={}", len(systems))
            return systems

    def insert_system(self, system_info: SystemInfo) -> None:
        with self._write_lock:
            self._run_async(self._insert_system_async(system_info))

    def get_system(self, system_name: str) -> SystemInfo | None:
        try:
            return self._run_async(self._get_system_async(system_name))
        except Exception:
            self.logger.exception("Lookup failed for system={}", system_name)
            return None

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None:
        with self._write_lock:
            self._run_async(self._add_neighbors_async(system_info, new_neighbors))

    def get_all_systems(self) -> list[SystemInfo]:
        return self._run_async(self._get_all_systems_async())


if __name__ == "__main__":
    main()
