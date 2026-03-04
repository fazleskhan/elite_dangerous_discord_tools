from collections import deque
import constants
import logging
from typing import Any, Callable

"""Breadth-first traversal used to build/solve routes between systems."""

logger = logging.getLogger(__name__)


SystemInfo = dict[str, Any]
FetchInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[[SystemInfo], list[SystemInfo] | None]
DistanceFn = Callable[[str, str], float]


def main() -> None: ...


def travel(
    func_fetch_info: FetchInfoFn,
    func_fetch_neighbors: FetchNeighborsFn,
    start_name: str,
    destination_name: str,
    max_count: int,
    min_distance: int,
    max_distance: int,
    func_calc_system_distance: DistanceFn,
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
    distance_to_destination = func_calc_system_distance(start_name, destination_name)
    previous_distance = distance_to_destination

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

        distance_to_destination = func_calc_system_distance(
            current_node, destination_name
        )
        logger.debug(
            "Current distance estimate %s -> %s: %s",
            current_node,
            destination_name,
            distance_to_destination,
        )

        if distance_to_destination >= previous_distance * 1.05:
            logger.debug(
                r"current node is more than 5% further ways than the previous node"
            )
            continue
        elif distance_to_destination < previous_distance:
            previous_distance = distance_to_destination

        if current_node == destination_name:
            logger.info("Destination reached: %s", destination_name)
            return path

        system_info = func_fetch_info(current_node)
        if not system_info:
            logger.debug("Skipping node with missing system info: %s", current_node)
            continue

        # Expand the frontier one hop at a time (standard BFS).
        neighbors = func_fetch_neighbors(system_info)
        if not neighbors:
            continue

        for adjacent_neighbor in neighbors:
            adjacent_name = adjacent_neighbor[constants.system_info_name_field]
            adjacent_distance = adjacent_neighbor.get("distance")
            if adjacent_distance is None:
                adjacent_distance = func_calc_system_distance(
                    current_node, adjacent_name
                )

            if not (min_distance <= adjacent_distance <= max_distance):
                logger.debug(
                    f"system distance {adjacent_distance} is not between {min_distance} and {max_distance}"
                )
                continue

            if adjacent_name not in visited:
                adjacent_info = func_fetch_info(adjacent_name)
                if not adjacent_info:
                    continue
                visited.add(adjacent_name)
                new_path = list(path)
                new_path.append(adjacent_name)
                queue.append(new_path)
    logger.info(
        "No route found from %s to %s within max_count=%s",
        start_name,
        destination_name,
        max_count,
    )
    return None


if __name__ == "__main__":
    main()
