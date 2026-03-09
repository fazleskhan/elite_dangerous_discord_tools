import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, Protocol

import ed_factory
import edgis_cache
import psutil
from loguru import logger
from ed_constants import (
    system_info_coords_field,
    system_info_name_field,
    system_info_x_field,
    system_info_y_field,
    system_info_z_field,
)

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


class EDBulkLoad:
    """Bulk loader with injected cache functions for IoC-friendly composition."""

    def __init__(
        self,
        fetch_system_info_fn: FetchInfoFn,
        fetch_neighbors_fn: FetchNeighborsFn,
    ) -> None:
        self.fetch_system_info_fn = fetch_system_info_fn
        self.fetch_neighbors_fn = fetch_neighbors_fn
        logger.debug("BulkLoadService initialized")

    @staticmethod
    def create(cache: CacheProtocol, logging_utils: Any) -> "EDBulkLoad":
        return EDBulkLoad(
            fetch_system_info_fn=cache.find_system_info,
            fetch_neighbors_fn=cache.find_system_neighbors,
        )

    def load(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        # Entry point used by CLI and Discord: walk neighbor graph and return
        # deterministic visit order up to the caller-provided node limit.
        logger.debug(
            "EDBulkLoad.load called initial_system_count={} max_nodes_visited={}",
            len(initial_system_names),
            max_nodes_visited,
        )
        if max_nodes_visited <= 0:
            logger.warning(
                "Skipping bulk load due to non-positive max_nodes_visited={}",
                max_nodes_visited,
            )
            return []

        # Queue system payloads (not just names) so we can expand neighbors
        # without re-fetching metadata when payloads are already complete.
        queue: deque[SystemInfo] = deque()
        # `visited` is the dedupe guard; `visit_order` preserves caller-visible order.
        visited: set[str] = set()
        visit_order: list[str] = []

        # Seed BFS frontier from user-provided systems.
        for system_name in initial_system_names:
            normalized = system_name.strip()
            if not normalized or normalized in visited:
                logger.debug("Skipping duplicate/blank seed system={}", system_name)
                continue
            visited.add(normalized)
            visit_order.append(normalized)
            system_info = self.fetch_system_info_fn(normalized)
            if system_info is not None:
                queue.append(system_info)
                logger.debug("Seeded initial system={} into frontier", normalized)
            else:
                logger.debug("Seed system info not found for system={}", normalized)
            if len(visited) >= max_nodes_visited:
                logger.debug("Reached max_nodes_visited during seed phase")
                return visit_order

        worker_count = _physical_core_count()
        logger.debug("Using bulk load worker pool size={}", worker_count)

        # Expand outward one hop at a time until queue is exhausted or max cap is hit.
        # Frontier items are fetched in parallel, but yielded in frontier order.
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            while queue and len(visited) < max_nodes_visited:
                frontier = list(queue)
                queue.clear()
                logger.debug(
                    "Processing frontier_size={} visited_count={}",
                    len(frontier),
                    len(visited),
                )

                # map() runs frontier expansion across the worker pool and
                # yields in input order so traversal remains predictable.
                for neighbors in executor.map(self._fetch_neighbors, frontier):
                    logger.debug("Fetched neighbor_count={}", len(neighbors))
                    for neighbor in neighbors:
                        neighbor_name = neighbor.get(system_info_name_field)
                        if not isinstance(neighbor_name, str):
                            logger.debug("Skipping neighbor with invalid name payload={}", neighbor)
                            continue
                        if neighbor_name in visited:
                            logger.debug("Skipping already-visited neighbor={}", neighbor_name)
                            continue

                        visited.add(neighbor_name)
                        visit_order.append(neighbor_name)
                        logger.debug(
                            "Visited neighbor={} visited_count={}",
                            neighbor_name,
                            len(visited),
                        )

                        # Prefer neighbor payload reuse to avoid extra cache lookups.
                        queued_neighbor = self._neighbor_as_system_info(neighbor)
                        if queued_neighbor is None:
                            # Some backends return light neighbor records; resolve to a
                            # full system payload only when needed for subsequent expansion.
                            queued_neighbor = self.fetch_system_info_fn(neighbor_name)
                            logger.debug(
                                "Neighbor payload incomplete; fetched full system info for {}",
                                neighbor_name,
                            )

                        if queued_neighbor is not None:
                            queue.append(queued_neighbor)
                            logger.debug("Queued neighbor={} for expansion", neighbor_name)
                        else:
                            logger.debug("Skipping enqueue; system info unavailable for {}", neighbor_name)
                        if len(visited) >= max_nodes_visited:
                            logger.debug("Reached max_nodes_visited during traversal")
                            break

                    if len(visited) >= max_nodes_visited:
                        break

                # Mirror existing project pattern: lightweight periodic progress updates.
                if (len(visited) & 0x1FF) == 0:
                    progress_callback(
                        f"Loaded {len(visited)} of {max_nodes_visited} systems"
                    )

        logger.debug("EDBulkLoad.load completed visited_count={}", len(visit_order))
        return visit_order

    def _neighbor_as_system_info(self, neighbor: SystemInfo) -> SystemInfo | None:
        # We only treat neighbor payloads as expandable system records when
        # the coordinate triplet is present.
        coords = neighbor.get(system_info_coords_field)
        if not isinstance(coords, dict):
            return None
        if (
            system_info_x_field not in coords
            or system_info_y_field not in coords
            or system_info_z_field not in coords
        ):
            return None
        return neighbor

    def _fetch_neighbors(self, system_info: SystemInfo) -> list[SystemInfo]:
        # Worker task: isolate neighbor expansion call for thread pool mapping.
        system_name = system_info.get(system_info_name_field)
        logger.debug("Fetching neighbors for system={}", system_name)
        return self.fetch_neighbors_fn(system_info) or []


# Backward-compatible alias used by existing tests/imports.
BulkLoadService = EDBulkLoad


def _physical_core_count() -> int:
    detected = psutil.cpu_count(logical=False)
    if detected is not None and detected > 0:
        return detected
    # Fallback: logical core count when physical count isn't available.
    return max(1, psutil.cpu_count(logical=True) or 1)


def create_bulk_loader(
    datasource_name: str | None = None,
    datasource_type: str | None = None,
) -> EDBulkLoad:
    # Composition root: backend selection is deferred to ed_factory/env config.
    datasource = ed_factory.create_datasource(
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )
    cache = edgis_cache.EDGisCache.create(datasource)
    return EDBulkLoad.create(cache, logging_utils=None)


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
