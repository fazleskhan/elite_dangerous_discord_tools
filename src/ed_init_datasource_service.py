from __future__ import annotations

import threading
from pathlib import Path

from constants import default_init_dir
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDInitDatasourceService:
    def __init__(self, datasource: DatasourceProtocol, logger: LoggingProtocol) -> None:
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        self._database = datasource
        self._lock = threading.RLock()
        self._logger.debug("EDInitDatasourceService initialized")

    def run(self, import_dir: str | Path = default_init_dir) -> None:
        self._logger.info("Initializing datasource from {}", import_dir)
        # Initialization can be expensive/mutating; keep it single-threaded per instance.
        with self._lock:
            self._database.init_datasource(import_dir)
