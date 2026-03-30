from __future__ import annotations

import threading
from pathlib import Path

from ed_constants import default_init_dir
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDInitDatasourceService:
    """Initialize the backing datasource from a seed import directory.

    The service exists so entrypoints can depend on a small protocol that owns
    the logging and synchronization around datasource initialization instead of
    calling the datasource directly.
    """

    def __init__(self, datasource: DatasourceProtocol, logger: LoggingProtocol) -> None:
        """Store the datasource dependency and initialize the mutation lock.

        Datasource initialization is mutating and potentially expensive, so the
        service keeps a re-entrant lock to ensure one initialization flow runs
        at a time per service instance.
        """
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        self._database = datasource
        self._lock = threading.RLock()
        self._logger.debug("EDInitDatasourceService initialized")

    def run(self, import_dir: str | Path = default_init_dir) -> None:
        """Load initial records into the datasource from the given directory.

        The method logs the requested import directory and then serializes the
        actual datasource initialization so concurrent callers cannot overlap
        mutating import work.
        """
        self._logger.info("Initializing datasource from {}", import_dir)
        # Initialization can be expensive/mutating; keep it single-threaded per instance.
        with self._lock:
            self._database.init_datasource(import_dir)
