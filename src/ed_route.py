import edgis_cache
import db
import ed_bfs
import shutil
import constants
import os
from dotenv import load_dotenv


def main(): ...


class EDRouteService:
    """Routing service with injected dependencies for easier testing."""

    def __init__(
        self,
        db_path,
        database,
        cache,
        travel_fn,
        file_exists,
        copy_file,
        script_file,
        default_preload_db,
    ):
        self.db_path = db_path
        self.database = database
        self.cache = cache
        self.travel_fn = travel_fn
        self.file_exists = file_exists
        self.copy_file = copy_file
        self.script_file = script_file
        self.default_preload_db = default_preload_db

    @staticmethod
    def create(
        db_factory=db.DB,
        cache_factory=edgis_cache.EDGisCache.create,
        travel_fn=ed_bfs.travel,
        file_exists=os.path.exists,
        copy_file=shutil.copy,
        script_file=__file__,
        default_preload_db=constants.pre_initiazlied_db_filename,
    ):
        load_dotenv()
        default_db_path = script_file.replace("src", "data").replace(".py", ".db")
        resolved_db_path = os.getenv("DB_LOCATION", default_db_path)
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
        return service

    def _resolve_preload_source_path(self, preinit_db_filename):
        if os.path.isabs(preinit_db_filename):
            return preinit_db_filename

        script_dir = os.path.dirname(os.path.realpath(self.script_file))
        data_dir = os.path.normpath(os.path.join(script_dir, "..", "data"))
        data_source_path = os.path.join(data_dir, preinit_db_filename)
        if self.file_exists(data_source_path):
            return data_source_path

        return os.path.join(script_dir, preinit_db_filename)

    def _ensure_preloaded_db(self, preinit_db_filename):
        if self.file_exists(self.db_path):
            return
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        source_path = self._resolve_preload_source_path(preinit_db_filename)
        self.copy_file(source_path, self.db_path)

    def get_system_info(self, system_name):
        return self.cache.find_system_info(system_name)

    def get_all_system_names(self):
        results = []
        system_infos = self.database.get_all_systems()
        for system_info in system_infos:
            results.append(system_info[constants.system_info_name_field])
        return results

    def path(self, initial_system_name, destination_name, max_systems=100):
        return self.travel_fn(
            self.cache.find_system_info,
            self.cache.find_system_neighbors,
            initial_system_name,
            destination_name,
            max_systems,
        )


if __name__ == "__main__":
    main()
