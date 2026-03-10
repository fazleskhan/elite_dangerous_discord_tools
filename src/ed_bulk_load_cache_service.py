from __future__ import annotations

from ed_protocols import BulkLoadProtocol, LoggingProtocol, ProgressFn


class EDBulkLoadCacheService:
    def __init__(self, bulk_load: BulkLoadProtocol, logging_utils: LoggingProtocol) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self._logging_utils = logging_utils
        if bulk_load is None:
            raise ValueError("bulk_load of type BulkLoadProtocol is required")
        else:
            self._bulk_load = bulk_load
        self._logging_utils.debug("EDBulkLoadCacheService initialized")

    @staticmethod
    def create(
        bulk_load: BulkLoadProtocol, logging_utils: LoggingProtocol
    ) -> "EDBulkLoadCacheService":
        return EDBulkLoadCacheService(bulk_load, logging_utils)

    def load(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        self._logging_utils.info(
            "Bulk loading cache from seeds={} max_nodes_visited={}",
            initial_system_names,
            max_nodes_visited,
        )
        return self._bulk_load.load(
            initial_system_names=initial_system_names,
            max_nodes_visited=max_nodes_visited,
            progress_callback=progress_callback,
        )
