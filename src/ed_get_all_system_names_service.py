from __future__ import annotations

import threading

from constants import system_info_name_field
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDGetAllSystemNamesService:
    def __init__(self, datasource: DatasourceProtocol, logger: LoggingProtocol) -> None:
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        self._database = datasource
        self._lock = threading.RLock()
        self._logger.debug("EDGetAllSystemNamesService initialized")

    def run(self) -> list[str]:
        # Serialize DB reads through a local lock to keep service calls predictable.
        with self._lock:
            system_infos = self._database.get_all_systems()
        results = [
            system_info[system_info_name_field]
            for system_info in system_infos
            if system_info_name_field in system_info
        ]
        self._logger.debug("Collected {} system names", len(results))
        return results
