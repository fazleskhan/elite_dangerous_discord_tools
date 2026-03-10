from collections import deque
from loguru import logger
import time
from typing import Any

from ed_constants import system_info_name_field
from ed_logging_utils import EDLoggingUtils
from ed_protocols import (
    DistanceFn,
    FetchInfoFn,
    FetchNeighborsFn,
    LoggingProtocol,
    ProgressFn,
    SystemInfo,
)
"""Breadth-first traversal used to build/solve routes between systems."""


def main() -> None: ...


def _reconstruct_path(
    parents: dict[str, str | None], destination_name: str
) -> list[str]:
    path: list[str] = []
    cursor: str | None = destination_name
    while cursor is not None:
        path.append(cursor)
        cursor = parents.get(cursor)
    path.reverse()
    return path


def travel(
    func_fetch_info: FetchInfoFn,
    func_fetch_neighbors: FetchNeighborsFn,
    start_name: str,
    destination_name: str,
    max_count: int,
    min_distance: int,
    max_distance: int,
    func_calc_system_distance: DistanceFn,
    progress_callback: ProgressFn,
) -> list[str] | None:
    logger.info(
        "Starting BFS travel from {} to {} with max_count={}",
        start_name,
        destination_name,
        max_count,
    )

    if start_name == destination_name:
        logger.debug("Start and destination are identical: {}", start_name)
        return [start_name]

    node_count = 0
    distance_to_destination = func_calc_system_distance(start_name, destination_name)
    previous_distance = distance_to_destination

    system_name_field = system_info_name_field
    queue: deque[str] = deque([start_name])
    visited: set[str] = {start_name}
    parents: dict[str, str | None] = {start_name: None}
    # Throttle progress updates so callers (CLI/Discord) aren't spammed.
    last_progress_report = time.monotonic()

    while queue:

        # Bound total visited nodes to cap runtime for expensive graph walks.
        if node_count > max_count:
            logger.warning("Reached max number of systems: {}", max_count)
            break
        else:
            node_count += 1
            if (node_count & 0x1FF) == 0:
                now = time.monotonic()
                if now - last_progress_report >= 30:
                    # Message format is consumed by CLI/Discord progress handlers.
                    progress_callback(f"Analyzed {node_count} of {max_count} systems")
                    last_progress_report = now

        current_node = queue.popleft()

        distance_to_destination = func_calc_system_distance(
            current_node, destination_name
        )

        if distance_to_destination >= previous_distance * 1.05:
            continue
        elif distance_to_destination < previous_distance:
            previous_distance = distance_to_destination

        if current_node == destination_name:
            logger.info("Destination reached: {}", destination_name)
            return _reconstruct_path(parents, destination_name)

        system_info = func_fetch_info(current_node)
        if not system_info:
            logger.debug("Skipping node with missing system info: {}", current_node)
            continue

        # Expand the frontier one hop at a time (standard BFS).
        neighbors = func_fetch_neighbors(system_info)
        if not neighbors:
            continue

        for adjacent_neighbor in neighbors:
            adjacent_name = adjacent_neighbor[system_name_field]
            adjacent_distance = adjacent_neighbor.get("distance")
            if adjacent_distance is None:
                adjacent_distance = func_calc_system_distance(
                    current_node, adjacent_name
                )

            if not (min_distance <= adjacent_distance <= max_distance):
                continue

            if adjacent_name not in visited:
                visited.add(adjacent_name)
                parents[adjacent_name] = current_node
                queue.append(adjacent_name)
    logger.info(
        "No route found from {} to {} within max_count={}",
        start_name,
        destination_name,
        max_count,
    )
    return None


class EDBfs:
    """OO wrapper for BFS traversal with IoC-friendly construction."""

    def __init__(
        self,
        fetch_info_fn: FetchInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
        logging_utils: LoggingProtocol,
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        self._fetch_info_fn = fetch_info_fn
        self._fetch_neighbors_fn = fetch_neighbors_fn
        self._logging_utils = logging_utils

    @staticmethod
    def create(cache: Any, logging_utils: LoggingProtocol | None) -> "EDBfs":
        return EDBfs(
            fetch_info_fn=cache.find_system_info,
            fetch_neighbors_fn=cache.find_system_neighbors,
            logging_utils=logging_utils,
        )

    def travel(
        self,
        start_name: str,
        destination_name: str,
        max_count: int,
        min_distance: int,
        max_distance: int,
        calc_distance_fn: DistanceFn,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        return travel(
            self._fetch_info_fn,
            self._fetch_neighbors_fn,
            start_name,
            destination_name,
            max_count,
            min_distance,
            max_distance,
            calc_distance_fn,
            progress_callback,
        )


if __name__ == "__main__":
    main()
