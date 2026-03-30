from __future__ import annotations

import threading

from ed_protocols import CacheProtocol, LoggingProtocol, SystemInfo


class EDGetSystemInfoService:
    def __init__(self, cache: CacheProtocol, logger: LoggingProtocol) -> None:
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if cache is None:
            raise ValueError("cache of type CacheProtocol is required")
        self._cache = cache
        self._lock = threading.RLock()
        self._logger.debug("EDGetSystemInfoService initialized")

    def run(self, system_name: str) -> SystemInfo | None:
        self._logger.debug(
            "Fetching system info via service for system={}",
            system_name,
        )
        # Lock around cache access so concurrent callers share one consistent path.
        with self._lock:
            return self._cache.find_system_info(system_name)
