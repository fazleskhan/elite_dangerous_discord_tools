import edgis_cache
import db
import ed_bfs
import shutil
import constants
import os
import asyncio
import threading
from concurrent.futures import Future
import logging
from dotenv import load_dotenv
from typing import Any, Callable, Protocol

"""Service layer that composes DB/cache dependencies and route search."""

logger = logging.getLogger(__name__)


SystemInfo = dict[str, Any]


class DBProtocol(Protocol):
    def get_all_systems(self) -> list[SystemInfo]: ...


class CacheProtocol(Protocol):
    def find_system_info(self, system_name: str) -> SystemInfo | None: ...
    def find_system_neighbors(
        self, system_info: SystemInfo
    ) -> list[SystemInfo] | None: ...


def main() -> None: ...


class EDRouteService:
    """Routing service with injected dependencies for easier testing."""

    def __init__(
        self,
        db_path: str,
        database: DBProtocol | None,
        cache: CacheProtocol | None,
        travel_fn: Callable[..., list[str] | None],
        file_exists: Callable[[str], bool],
        copy_file: Callable[[str, str], str],
        script_file: str,
        default_preload_db: str,
    ) -> None:
        self.db_path = db_path
        self.database = database
        self.cache = cache
        self.travel_fn = travel_fn
        self.file_exists = file_exists
        self.copy_file = copy_file
        self.script_file = script_file
        self.default_preload_db = default_preload_db
        self.logger = logger

    @staticmethod
    def create(
        db_factory: Callable[[str], DBProtocol] = db.DB,
        cache_factory: Callable[
            [DBProtocol], CacheProtocol
        ] = edgis_cache.EDGisCache.create,
        travel_fn: Callable[..., list[str] | None] = ed_bfs.travel,
        file_exists: Callable[[str], bool] = os.path.exists,
        copy_file: Callable[[str, str], str] = shutil.copy,
        script_file: str = __file__,
        default_preload_db: str = constants.pre_initiazlied_db_filename,
    ) -> "EDRouteService":
        load_dotenv()
        # Keep a stable default DB path while allowing env override.
        default_db_path = script_file.replace("src", "data").replace(".py", ".db")
        resolved_db_path = os.getenv("DB_LOCATION", default_db_path)
        logger.debug("Creating EDRouteService with db_path=%s", resolved_db_path)
        service = EDRouteService(
            db_path=resolved_db_path,
            database=None,
            cache=None,
            travel_fn=travel_fn,
            file_exists=file_exists,
            copy_file=copy_file,
            script_file=script_file,
            default_preload_db=default_preload_db,
        )
        service._ensure_preloaded_db(default_preload_db)
        service.database = db_factory(resolved_db_path)
        service.cache = cache_factory(service.database)
        service.logger.info("EDRouteService initialized with db_path=%s", resolved_db_path)
        return service

    def _resolve_preload_source_path(self, preinit_db_filename: str) -> str:
        if os.path.isabs(preinit_db_filename):
            return preinit_db_filename

        script_dir = os.path.dirname(os.path.realpath(self.script_file))
        data_dir = os.path.normpath(os.path.join(script_dir, "..", "data"))
        data_source_path = os.path.join(data_dir, preinit_db_filename)
        # Prefer `<repo>/data/<filename>` and fall back to the script folder.
        if self.file_exists(data_source_path):
            return data_source_path

        return os.path.join(script_dir, preinit_db_filename)

    def _ensure_preloaded_db(self, preinit_db_filename: str) -> None:
        # First run: copy preloaded DB to the configured writable target.
        if self.file_exists(self.db_path):
            self.logger.debug("DB already exists at %s", self.db_path)
            return
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        source_path = self._resolve_preload_source_path(preinit_db_filename)
        self.logger.info("Copying preloaded DB from %s to %s", source_path, self.db_path)
        self.copy_file(source_path, self.db_path)

    def get_system_info(self, system_name: str) -> SystemInfo | None:
        if self.cache is None:
            self.logger.warning("Route cache is not initialized for get_system_info")
            return None
        self.logger.debug("Fetching system info via cache for system=%s", system_name)
        return self.cache.find_system_info(system_name)

    def get_all_system_names(self) -> list[str]:
        if self.database is None:
            self.logger.warning("Database is not initialized for get_all_system_names")
            return []
        results = []
        system_infos = self.database.get_all_systems()
        for system_info in system_infos:
            results.append(system_info[constants.system_info_name_field])
        self.logger.debug("Collected %s system names", len(results))
        return results

    async def path(
        self, initial_system_name: str, destination_name: str, max_systems: int = 100
    ) -> list[str] | None:
        if self.cache is None:
            self.logger.warning("Route cache is not initialized for path")
            return None
        self.logger.info(
            "Calculating path source=%s destination=%s max_systems=%s",
            initial_system_name,
            destination_name,
            max_systems,
        )

        result: Future[list[str] | None] = Future()

        def _worker() -> None:
            try:
                route_result = self.travel_fn(
                    self.cache.find_system_info,
                    self.cache.find_system_neighbors,
                    initial_system_name,
                    destination_name,
                    max_systems,
                )
                result.set_result(route_result)
            except Exception as exc:
                result.set_exception(exc)

        threading.Thread(target=_worker, daemon=True).start()
        while not result.done():
            await asyncio.sleep(0.01)
        route = result.result()
        self.logger.info("Path calculation complete found=%s", route is not None)
        return route


if __name__ == "__main__":
    main()
