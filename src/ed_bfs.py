from collections import deque
import constants
import logging
from typing import Any, Callable

"""Breadth-first traversal used to build/solve routes between systems."""

logger = logging.getLogger(__name__)


SystemInfo = dict[str, Any]
FetchInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[[SystemInfo], list[SystemInfo]]


def main() -> None: ...


def travel(
    func_fetch_info: FetchInfoFn,
    func_fetch_neighbors: FetchNeighborsFn,
    start_name: str,
    destination_name: str = "",
    max_count: int = 10,
) -> list[str] | None:
    logger.info(
        "Starting BFS travel from %s to %s with max_count=%s",
        start_name,
        destination_name,
        max_count,
    )

    if start_name == destination_name:
        logger.debug("Start and destination are identical: %s", start_name)
        return [start_name]

    node_count = 0

    queue: deque[list[str]] = deque([[start_name]])
    visited: set[str] = {start_name}

    while queue:

        # Bound total visited nodes to cap runtime for expensive graph walks.
        if node_count > max_count:
            logger.warning("Reached max number of systems: %s", max_count)
            break
        else:
            node_count += 1

        path = queue.popleft()
        current_node = path[-1]

        if current_node == destination_name:
            logger.info("Destination reached: %s", destination_name)
            return path

        system_info = func_fetch_info(current_node)
        if not system_info:
            logger.debug("Skipping node with missing system info: %s", current_node)
            continue

        # Expand the frontier one hop at a time (standard BFS).
        for adjacent_neighbor in func_fetch_neighbors(system_info):
            if adjacent_neighbor[constants.system_info_name_field] not in visited:
                adjacent_neighbor = func_fetch_info(
                    adjacent_neighbor[constants.system_info_name_field]
                )
                if not adjacent_neighbor:
                    continue
                visited.add(adjacent_neighbor[constants.system_info_name_field])
                new_path = list(path)
                new_path.append(adjacent_neighbor[constants.system_info_name_field])
                queue.append(new_path)
    logger.info(
        "No route found from %s to %s within max_count=%s",
        start_name,
        destination_name,
        max_count,
    )


if __name__ == "__main__":
    main()
