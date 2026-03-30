from __future__ import annotations

import threading

from ed_constants import system_info_name_field
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDGetAllSystemNamesService:
    """Read and normalize all known system names from the datasource.

    The service wraps the raw datasource call so upper layers can depend on a
    small protocol that owns locking, extraction of the name field, and
    lightweight logging in one place.
    """

    def __init__(self, datasource: DatasourceProtocol, logger: LoggingProtocol) -> None:
        """Store datasource dependencies and initialize the service lock.

        The lock keeps repeated callers from interleaving multi-record reads in
        ways that would make behavior less predictable during tests and
        concurrent application usage.
        """
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if datasource is None:
            raise ValueError("datasource of type DatasourceProtocol is required")
        self._database = datasource
        self._lock = threading.RLock()
        self._logger.debug("EDGetAllSystemNamesService initialized")

    def run(self) -> list[str]:
        """Return every stored system name in datasource order.

        The service serializes the datasource read, extracts the name field from
        each system payload, and returns only records that actually contain a
        usable system name.
        """
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
