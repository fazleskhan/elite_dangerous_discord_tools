import asyncio
import threading
from typing import Any

import aiohttp
from ed_protocols import LoggingProtocol

from ed_constants import (
    query_param_q,
    system_info_x_field,
    system_info_y_field,
    system_info_z_field,
    value_key,
)

"""Thin HTTP client wrappers for EDGIS system and neighbor lookups."""


class EDGis:
    """OO gateway wrapper around EDGIS HTTP lookups."""

    # https://github.com/elitedangereuse/ed_edgis/blob/c7f98f266a7536530232a9946268bbb0dd77b63c/api/systems.py#L515
    # https://ed_edgis.elitedangereuse.fr/neighbors?x=<x_value>&y=<y_value>&z=<z_value>&radius=20
    _fetch_neighbors_uri: str = r"https://ed_edgis.elitedangereuse.fr/neighbors"
    # https://github.com/elitedangereuse/ed_edgis/blob/c7f98f266a7536530232a9946268bbb0dd77b63c/api/systems.py#L1078
    # https://ed_edgis.elitedangereuse.fr/coords?q=<url_encoded_system_name>
    _fetch_coords_uri: str = r"https://ed_edgis.elitedangereuse.fr/coords"

    def __init__(self, logger: LoggingProtocol):
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger

    @staticmethod
    def _run_async(coro: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        output: dict[str, Any] = {}
        error: dict[str, BaseException] = {}

        def _worker() -> None:
            try:
                output[value_key] = asyncio.run(coro)
            except BaseException as exc:
                error[value_key] = exc

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        worker.join()

        if value_key in error:
            raise error[value_key]

        return output.get(value_key)

    @staticmethod
    async def _fetch_json(url: str, params: dict[str, Any]) -> Any:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as response:
                response.raise_for_status()
                return await response.json()

    def fetch_system_info(self, system_name: str) -> dict[str, Any] | None:
        self._logger.debug("Fetching system info for system={}", system_name)
        try:
            # The API expects the system name under the `q` query parameter.
            return EDGis._run_async(
                EDGis._fetch_json(EDGis._fetch_coords_uri, {query_param_q: system_name})
            )
        except (aiohttp.ClientError, TimeoutError):
            self._logger.exception(
                "Failed to fetch system info for system={}", system_name
            )
            return None

    def fetch_neighbors(
        self, x: float | int, y: float | int, z: float | int
    ) -> list[dict[str, Any]] | None:
        self._logger.debug("Fetching neighbors for coordinates x={} y={} z={}", x, y, z)
        try:
            # EDGIS ed_defaults to a 20ly radius when radius is omitted.
            return EDGis._run_async(
                EDGis._fetch_json(
                    EDGis._fetch_neighbors_uri,
                    {
                        system_info_x_field: x,
                        system_info_y_field: y,
                        system_info_z_field: z,
                    },
                )
            )
        except (aiohttp.ClientError, TimeoutError):
            self._logger.exception(
                "Failed to fetch neighbors for coordinates x={} y={} z={}", x, y, z
            )
            return None
