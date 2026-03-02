import edgis_cache
import db
import ed_bfs
import shutil
import constants
import os


def main(): ...


class EDRouteService:
    """Routing service with injected dependencies for easier testing."""

    def __init__(
        self,
        db_path,
        db_factory=db.DB,
        cache_factory=edgis_cache.Ed_Cache,
        travel_fn=ed_bfs.travel,
        file_exists=os.path.exists,
        copy_file=shutil.copy,
        script_file=__file__,
        default_preload_db=constants.pre_initiazlied_db_filename,
    ):
        self.db_path = db_path
        self.db_factory = db_factory
        self.cache_factory = cache_factory
        self.travel_fn = travel_fn
        self.file_exists = file_exists
        self.copy_file = copy_file
        self.script_file = script_file
        self.default_preload_db = default_preload_db

    @staticmethod
    def create(
        db_path=None,
        db_factory=db.DB,
        cache_factory=edgis_cache.Ed_Cache,
        travel_fn=ed_bfs.travel,
        file_exists=os.path.exists,
        copy_file=shutil.copy,
        script_file=__file__,
        default_preload_db=constants.pre_initiazlied_db_filename,
    ):
        default_db_path = script_file.replace("src", "data").replace(".py", ".db")
        resolved_db_path = db_path or os.getenv("DB_LOCATION", default_db_path)
        return EDRouteService(
            db_path=resolved_db_path,
            db_factory=db_factory,
            cache_factory=cache_factory,
            travel_fn=travel_fn,
            file_exists=file_exists,
            copy_file=copy_file,
            script_file=script_file,
            default_preload_db=default_preload_db,
        )

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

    def _new_cache(self):
        self._ensure_preloaded_db(self.default_preload_db)
        database = self.db_factory(self.db_path)
        return self.cache_factory(database)

    def get_system_info(self, system_name):
        cache = self._new_cache()
        return cache.find_system_info(system_name)

    def get_all_system_names(self):
        self._ensure_preloaded_db(self.default_preload_db)
        results = []
        database = self.db_factory(self.db_path)
        system_infos = database.get_all_systems()
        for system_info in system_infos:
            results.append(system_info[constants.system_info_name_field])
        return results

    def path(
        self,
        initial_system_name,
        destination_name,
        max_systems=100,
        preinit_db_filename=None,
    ):
        preinit_db_filename = preinit_db_filename or self.default_preload_db
        self._ensure_preloaded_db(preinit_db_filename)
        cache = self._new_cache()
        return self.travel_fn(
            cache.find_system_info,
            cache.find_system_neighbors,
            initial_system_name,
            destination_name,
            max_systems,
        )


_default_service = EDRouteService.create()


def fetch_system_info():
    return edgis_cache.find_system_info


def fetch_neighbors():
    return edgis_cache.find_system_neighbors


if __name__ == "__main__":
    main()
