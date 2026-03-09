import argparse
import edgis_cache
import ed_factory
from collections import deque
from typing import Any, Callable, Protocol
from loguru import logger
from logging_utils import setup_logging

"""Utility script to pre-populate local cache by traversing nearby systems."""

SystemInfo = dict[str, Any]
FetchInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[[SystemInfo], list[SystemInfo] | None]
ProgressFn = Callable[[str], None]


class CacheProtocol(Protocol):
    def find_system_info(self, system_name: str) -> SystemInfo | None: ...
    def find_system_neighbors(self, system_info: SystemInfo) -> list[SystemInfo] | None: ...


class BulkLoadService:
    """Bulk loader with injected cache functions for IoC-friendly composition."""

    def __init__(
        self,
        fetch_system_info_fn: FetchInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
    ) -> None:
        self.fetch_system_info_fn = fetch_system_info_fn
        self.fetch_neighbors_fn = fetch_neighbors_fn

    @staticmethod
    def create(cache: CacheProtocol) -> "BulkLoadService":
        return BulkLoadService(
            fetch_system_info_fn=cache.find_system_info,
            fetch_neighbors_fn=cache.find_system_neighbors,
        )

    def load(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        if max_nodes_visited <= 0:
            logger.warning(
                "Skipping bulk load due to non-positive max_nodes_visited={}",
                max_nodes_visited,
            )
            return []

        # Queue system payloads (not just names) so we can expand neighbors
        # without re-fetching metadata when payloads are already complete.
        queue: deque[SystemInfo] = deque()
        visited: set[str] = set()
        visit_order: list[str] = []

        # Seed BFS frontier from user-provided systems.
        for system_name in initial_system_names:
            normalized = system_name.strip()
            if not normalized or normalized in visited:
                continue
            visited.add(normalized)
            visit_order.append(normalized)
            system_info = self.fetch_system_info_fn(normalized)
            if system_info is not None:
                queue.append(system_info)
            if len(visited) >= max_nodes_visited:
                return visit_order

        # Expand outward one hop at a time until queue is exhausted or max cap is hit.
        while queue and len(visited) < max_nodes_visited:
            system_info = queue.popleft()
            neighbors = self.fetch_neighbors_fn(system_info) or []
            for neighbor in neighbors:
                neighbor_name = neighbor.get("name")
                if not isinstance(neighbor_name, str):
                    continue
                if neighbor_name in visited:
                    continue

                visited.add(neighbor_name)
                visit_order.append(neighbor_name)

                # Prefer neighbor payload reuse to avoid extra cache lookups.
                queued_neighbor = self._neighbor_as_system_info(neighbor)
                if queued_neighbor is None:
                    queued_neighbor = self.fetch_system_info_fn(neighbor_name)

                if queued_neighbor is not None:
                    queue.append(queued_neighbor)
                if len(visited) >= max_nodes_visited:
                    break

            # Mirror existing project pattern: lightweight periodic progress updates.
            if (len(visited) & 0x1FF) == 0:
                progress_callback(
                    f"Loaded {len(visited)} of {max_nodes_visited} systems"
                )

        return visit_order

    def _neighbor_as_system_info(self, neighbor: SystemInfo) -> SystemInfo | None:
        coords = neighbor.get("coords")
        if not isinstance(coords, dict):
            return None
        if "x" not in coords or "y" not in coords or "z" not in coords:
            return None
        return neighbor


def create_bulk_loader(
    datasource_name: str | None = None,
    datasource_type: str | None = None,
) -> BulkLoadService:
    # Composition root: backend selection is deferred to ed_factory/env config.
    datasource = ed_factory.create_datasource(
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )
    cache = edgis_cache.EDGisCache.create(datasource)
    return BulkLoadService.create(cache)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Pre-populate the local EDGIS cache by traversing nearby systems."
    )
    parser.add_argument(
        "initial_systems",
        help="Comma-separated list of starting systems (for example: Sol,Alpha Centauri)",
    )
    parser.add_argument(
        "max_nodes_visited",
        type=int,
        help="Maximum number of unique systems to visit",
    )
    args = parser.parse_args()
    initial_system_names = [
        system_name.strip()
        for system_name in args.initial_systems.split(",")
        if system_name.strip()
    ]
    logger.info(
        "Bulk load requested: initial_systems={} max_nodes_visited={}",
        initial_system_names,
        args.max_nodes_visited,
    )
    logic(initial_system_names, args.max_nodes_visited)


def logic(initial_system_names: list[str], max_nodes_visited: int) -> list[str]:
    logger.info(
        "Starting bulk load traversal from {} with max nodes={}",
        initial_system_names,
        max_nodes_visited,
    )
    bulk_loader = create_bulk_loader()
    loaded_systems = bulk_loader.load(
        initial_system_names=initial_system_names,
        max_nodes_visited=max_nodes_visited,
        progress_callback=lambda message: logger.info(message),
    )
    logger.info("Bulk load traversal completed loaded_systems={}", len(loaded_systems))
    return loaded_systems


if __name__ == "__main__":
    setup_logging()
    main()
