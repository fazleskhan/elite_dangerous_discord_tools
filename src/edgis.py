import asyncio
from loguru import logger
import threading
import aiohttp
from typing import Any

"""Thin HTTP client wrappers for EDGIS system and neighbor lookups."""


def main() -> None: ...


def _run_async(coro: Any) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    output: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            output["value"] = asyncio.run(coro)
        except BaseException as exc:
            error["value"] = exc

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join()

    if "value" in error:
        raise error["value"]

    return output.get("value")


async def _fetch_json(url: str, params: dict[str, Any]) -> Any:
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            return await response.json()


# https://github.com/elitedangereuse/edgis/blob/c7f98f266a7536530232a9946268bbb0dd77b63c/api/systems.py#L515
# https://edgis.elitedangereuse.fr/neighbors?x=<x_value>&y=<y_value>&z=<z_value>&radius=20
fetch_neighbors_uri: str = r"https://edgis.elitedangereuse.fr/neighbors"


def fetch_neighbors(
    x: float | int, y: float | int, z: float | int
) -> list[dict[str, Any]] | None:
    logger.debug("Fetching neighbors for coordinates x={} y={} z={}", x, y, z)
    try:
        # EDGIS defaults to a 20ly radius when radius is omitted.
        return _run_async(_fetch_json(fetch_neighbors_uri, {"x": x, "y": y, "z": z}))
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception(
            "Failed to fetch neighbors for coordinates x={} y={} z={}", x, y, z
        )
        return None


# https://github.com/elitedangereuse/edgis/blob/c7f98f266a7536530232a9946268bbb0dd77b63c/api/systems.py#L1078
# https://edgis.elitedangereuse.fr/coords?q=<url_encoded_system_name>
fetch_coords_uri: str = r"https://edgis.elitedangereuse.fr/coords"


def fetch_system_info(system_name: str) -> dict[str, Any] | None:
    logger.debug("Fetching system info for system={}", system_name)
    try:
        # The API expects the system name under the `q` query parameter.
        return _run_async(_fetch_json(fetch_coords_uri, {"q": system_name}))
    except (aiohttp.ClientError, asyncio.TimeoutError):
        logger.exception("Failed to fetch system info for system={}", system_name)
        return None


class EDGis:
    """OO gateway wrapper around EDGIS HTTP lookups."""

    def __init__(self, logging_utils: Any):
        self._logging_utils = logging_utils

    @staticmethod
    def create(logging_utils: Any) -> "EDGis":
        return EDGis(logging_utils)

    def fetch_system_info(self, system_name: str) -> dict[str, Any] | None:
        return fetch_system_info(system_name)

    def fetch_neighbors(
        self, x: float | int, y: float | int, z: float | int
    ) -> list[dict[str, Any]] | None:
        return fetch_neighbors(x, y, z)


if __name__ == "__main__":
    main()
