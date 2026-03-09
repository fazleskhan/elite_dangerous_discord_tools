import asyncio
from collections import deque
from typing import Any, Callable, Protocol

import ed_factory
import edgis_cache
from loguru import logger

"""Cache bulk-load helpers shared by CLI and Discord entrypoints."""

SystemInfo = dict[str, Any]
FetchInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[[SystemInfo], list[SystemInfo] | None]
ProgressFn = Callable[[str], None]


def main() -> None: ...


class CacheProtocol(Protocol):
    def find_system_info(self, system_name: str) -> SystemInfo | None: ...
    def find_system_neighbors(
        self, system_info: SystemInfo
    ) -> list[SystemInfo] | None: ...


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


def bulk_load(
    initial_system_names: list[str],
    max_nodes_visited: int,
    progress_callback: ProgressFn | None = None,
) -> list[str]:
    logger.info(
        "Starting bulk load traversal from {} with max nodes={}",
        initial_system_names,
        max_nodes_visited,
    )
    bulk_loader = create_bulk_loader()
    on_progress = progress_callback or (lambda message: logger.info(message))
    loaded_systems = bulk_loader.load(
        initial_system_names=initial_system_names,
        max_nodes_visited=max_nodes_visited,
        progress_callback=on_progress,
    )
    logger.info("Bulk load traversal completed loaded_systems={}", len(loaded_systems))
    return loaded_systems


async def bulk_load_async(
    initial_system_names: list[str],
    max_nodes_visited: int,
    progress_callback: ProgressFn | None = None,
) -> list[str]:
    return await asyncio.to_thread(
        bulk_load,
        initial_system_names,
        max_nodes_visited,
        progress_callback,
    )


if __name__ == "__main__":
    main()
