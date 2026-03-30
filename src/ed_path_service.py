from __future__ import annotations

import asyncio

from ed_protocols import (
    BfsProtocol,
    CalcSystemsDistanceProtocol,
    LoggingProtocol,
    ProgressFn,
)


class EDPathService:
    """Async-facing service for route calculations.

    The service adapts the synchronous BFS algorithm to async callers by moving
    traversal work onto a worker thread, allowing Discord and other async
    surfaces to await route calculation without blocking their event loops.
    """

    def __init__(
        self,
        bfs: BfsProtocol,
        calc_distance_service: CalcSystemsDistanceProtocol,
        logger: LoggingProtocol,
    ) -> None:
        """Store the BFS and distance collaborators used for route search.

        The service validates its dependencies eagerly so path requests fail at
        composition time rather than after an async command has already started.
        """
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger
        if bfs is None:
            raise ValueError("bfs of type BfsProtocol is required")
        self._bfs = bfs
        if calc_distance_service is None:
            raise ValueError(
                "calc_distance_service of type CalcSystemsDistanceProtocol is required"
            )
        self._calc_distance_service = calc_distance_service
        self._logger.debug("EDPathService initialized")

    async def run(
        self,
        initial_system_name: str,
        destination_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        """Calculate a route without blocking the caller's event loop.

        The method sends the synchronous BFS traversal to a worker thread, waits
        for the result asynchronously, and logs whether a route was found before
        returning the discovered path or `None`.
        """
        # Run BFS on a worker thread so async callers (CLI/Discord) stay responsive.
        route = await asyncio.to_thread(
            self._bfs.travel,
            initial_system_name,
            destination_name,
            max_systems,
            min_distance,
            max_distance,
            progress_callback,
        )
        self._logger.info("Path calculation complete found={}", route is not None)
        return route
