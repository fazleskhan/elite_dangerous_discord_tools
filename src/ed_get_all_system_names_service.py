from __future__ import annotations

import threading

from ed_constants import system_info_name_field
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDGetAllSystemNamesService:
    def __init__(self, datasource: DatasourceProtocol, logging_utils: LoggingProtocol) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self._logging_utils = logging_utils
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        else:
            self._database = datasource
        self._lock = threading.RLock()
        self._logging_utils.debug("EDGetAllSystemNamesService initialized")        

    @staticmethod
    def create(
        database: DatasourceProtocol, logging_utils: LoggingProtocol
    ) -> "EDGetAllSystemNamesService":
        return EDGetAllSystemNamesService(database, logging_utils)

    def run(self) -> list[str]:
        with self._lock:
            system_infos = self._database.get_all_systems()
        results = [
            system_info[system_info_name_field]
            for system_info in system_infos
            if system_info_name_field in system_info
        ]
        self._logging_utils.debug("Collected {} system names", len(results))
        return results
