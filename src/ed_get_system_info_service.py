from __future__ import annotations

import threading

from ed_protocols import CacheProtocol, LoggingProtocol, SystemInfo


class EDGetSystemInfoService:
    """Resolve a single system payload through the shared cache layer.

    The service keeps route-oriented callers isolated from the cache concrete by
    providing one narrow method that performs logging and serializes cache
    access in one place.
    """

    def __init__(self, cache: CacheProtocol, logger: LoggingProtocol) -> None:
        """Store cache dependencies and initialize the service lock.

        The lock ensures concurrent callers share one predictable access path
        through the cache, which keeps behavior stable across sync and async
        entrypoints.
        """
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if cache is None:
            raise ValueError("cache of type CacheProtocol is required")
        self._cache = cache
        self._lock = threading.RLock()
        self._logger.debug("EDGetSystemInfoService initialized")

    def run(self, system_name: str) -> SystemInfo | None:
        """Return cached or fetched system metadata for one system name.

        The service logs the lookup request and forwards it to the cache while
        holding a lock so concurrent callers do not race through divergent cache
        paths.
        """
        self._logger.debug(
            "Fetching system info via service for system={}",
            system_name,
        )
        # Lock around cache access so concurrent callers share one consistent path.
        with self._lock:
            return self._cache.find_system_info(system_name)
