from __future__ import annotations

import threading

from ed_constants import default_init_dir
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDInitDatasourceService:
    def __init__(
        self, datasource: DatasourceProtocol, logging_utils: LoggingProtocol
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self._logging_utils = logging_utils
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        else:
            self._database = datasource
        self._lock = threading.RLock()
        self._logging_utils.debug("EDInitDatasourceService initialized")

    @staticmethod
    def create(
        database: DatasourceProtocol, logging_utils: LoggingProtocol
    ) -> "EDInitDatasourceService":
        return EDInitDatasourceService(database, logging_utils)

    def run(self, import_dir: str = default_init_dir) -> None:
        self._logging_utils.info("Initializing datasource from {}", import_dir)
        # Initialization can be expensive/mutating; keep it single-threaded per instance.
        with self._lock:
            self._database.init_datasource(import_dir)
