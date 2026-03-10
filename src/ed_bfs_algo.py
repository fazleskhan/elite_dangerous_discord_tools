from collections import deque
import time

from ed_constants import distance, system_info_name_field
from ed_protocols import (
    DistanceFn,
    FetchNeighborsFn,
    FetchSystemInfoFn,
    LoggingProtocol,
    ProgressFn,
    SystemInfo,
)

"""Breadth-first traversal used to build/solve routes between systems."""


def main() -> None: ...


class EDBfsAlgo:
    """OO wrapper for BFS traversal with IoC-friendly construction."""

    def __init__(
        self,
        fetch_info_fn: FetchSystemInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
        distance_fn: DistanceFn,
        logging_utils: LoggingProtocol,
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self._logging_utils = logging_utils
        if fetch_info_fn is None:
            raise ValueError("fetch_info_fn of type FetchSystemInfoFn is required")
        else:
            self._fetch_info_fn = fetch_info_fn
        if fetch_neighbors_fn is None:
            raise ValueError("fetch_info_fn of type FetchSystemInfoFn is required")
        else:
            self._fetch_neighbors_fn = fetch_neighbors_fn
        if distance_fn is None:
            raise ValueError("distance_fn of type DistanceFn is required")
        else:
            self._distance_fn = distance_fn

    @staticmethod
    def create(
        fetch_system_info_fn: FetchSystemInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
        distance_fn: DistanceFn,
        logging_utils: LoggingProtocol,
    ) -> "EDBfsAlgo":
        return EDBfsAlgo(
            fetch_info_fn=fetch_system_info_fn,
            fetch_neighbors_fn=fetch_neighbors_fn,
            distance_fn=distance_fn,
            logging_utils=logging_utils,
        )

    @staticmethod
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
        self,
        start_name: str,
        destination_name: str,
        max_count: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        self._logging_utils.info(
            "Starting BFS travel from {} to {} with max_count={}",
            start_name,
            destination_name,
            max_count,
        )

        if start_name == destination_name:
            self._logging_utils.debug(
                "Start and destination are identical: {}", start_name
            )
            return [start_name]

        node_count = 0
        distance_to_destination = self._distance_fn(start_name, destination_name)
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
                self._logging_utils.warning(
                    "Reached max number of systems: {}", max_count
                )
                break
            else:
                node_count += 1
                if (node_count & 0x1FF) == 0:
                    now = time.monotonic()
                    if now - last_progress_report >= 30:
                        # Message format is consumed by CLI/Discord progress handlers.
                        progress_callback(
                            f"Analyzed {node_count} of {max_count} systems"
                        )
                        last_progress_report = now

            current_node = queue.popleft()

            distance_to_destination = self._distance_fn(current_node, destination_name)

            if distance_to_destination >= previous_distance * 1.05:
                continue
            elif distance_to_destination < previous_distance:
                previous_distance = distance_to_destination

            if current_node == destination_name:
                self._logging_utils.info("Destination reached: {}", destination_name)
                return EDBfsAlgo._reconstruct_path(parents, destination_name)

            system_info = self._fetch_info_fn(current_node)
            if not system_info:
                self._logging_utils.debug(
                    "Skipping node with missing system info: {}", current_node
                )
                continue

            # Expand the frontier one hop at a time (standard BFS).
            neighbors = self._fetch_neighbors_fn(system_info)
            if not neighbors:
                continue

            for adjacent_neighbor in neighbors:
                adjacent_name = adjacent_neighbor[system_name_field]
                adjacent_distance = adjacent_neighbor.get(distance)
                if adjacent_distance is None:
                    adjacent_distance = self._distance_fn(current_node, adjacent_name)

                if not (min_distance <= adjacent_distance <= max_distance):
                    continue

                if adjacent_name not in visited:
                    visited.add(adjacent_name)
                    parents[adjacent_name] = current_node
                    queue.append(adjacent_name)
        self._logging_utils.info(
            "No route found from {} to {} within max_count={}",
            start_name,
            destination_name,
            max_count,
        )
        return None


if __name__ == "__main__":
    main()
