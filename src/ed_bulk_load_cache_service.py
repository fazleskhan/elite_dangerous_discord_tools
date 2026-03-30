from __future__ import annotations

from ed_protocols import BulkLoadProtocol, LoggingProtocol, ProgressFn


class EDBulkLoadCacheService:
    def __init__(self, bulk_load: BulkLoadProtocol, logger: LoggingProtocol) -> None:
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if bulk_load is None:
            raise ValueError("bulk_load of type BulkLoadProtocol is required")
        self._bulk_load = bulk_load
        self._logger.debug("EDBulkLoadCacheService initialized")

    def load(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        # Thin service wrapper so route layer depends on protocol, not algorithm concrete.
        self._logger.info(
            "Bulk loading cache from seeds={} max_nodes_visited={}",
            initial_system_names,
            max_nodes_visited,
        )
        return self._bulk_load.load(
            initial_system_names=initial_system_names,
            max_nodes_visited=max_nodes_visited,
            progress_callback=progress_callback,
        )
