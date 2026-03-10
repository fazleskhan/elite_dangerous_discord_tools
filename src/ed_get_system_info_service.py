from __future__ import annotations

import threading

from ed_protocols import CacheProtocol, LoggingProtocol, SystemInfo


class EDGetSystemInfoService:
    def __init__(self, cache: CacheProtocol, logging_utils: LoggingProtocol) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self._logging_utils = logging_utils
        if cache is None:
            raise ValueError("cache of type CacheProtocol is required")
        else:
            self._cache = cache
        self._lock = threading.RLock()
        self._logging_utils.debug("EDGetSystemInfoService initialized")

    @staticmethod
    def create(
        cache: CacheProtocol, logging_utils: LoggingProtocol
    ) -> "EDGetSystemInfoService":
        return EDGetSystemInfoService(cache, logging_utils)

    def run(self, system_name: str) -> SystemInfo | None:
        self._logging_utils.debug(
            "Fetching system info via service for system={}",
            system_name,
        )
        # Lock around cache access so concurrent callers share one consistent path.
        with self._lock:
            return self._cache.find_system_info(system_name)
