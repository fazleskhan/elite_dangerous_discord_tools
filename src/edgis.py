import logging
import requests
from typing import Any

"""Thin HTTP client wrappers for EDGIS system and neighbor lookups."""

logger = logging.getLogger(__name__)


def main() -> None: ...


# https://github.com/elitedangereuse/edgis/blob/c7f98f266a7536530232a9946268bbb0dd77b63c/api/systems.py#L515
# https://edgis.elitedangereuse.fr/neighbors?x=<x_value>&y=<y_value>&z=<z_value>&radius=20
fetch_neighbors_uri: str = r"https://edgis.elitedangereuse.fr/neighbors"


def fetch_neighbors(
    x: float | int, y: float | int, z: float | int
) -> list[dict[str, Any]] | None:
    logger.debug("Fetching neighbors for coordinates x=%s y=%s z=%s", x, y, z)
    response = None
    try:
        # EDGIS defaults to a 20ly radius when radius is omitted.
        response = requests.get(fetch_neighbors_uri, params={"x": x, "y": y, "z": z})
        response.raise_for_status()
    except requests.RequestException:
        logger.exception(
            "Failed to fetch neighbors for coordinates x=%s y=%s z=%s", x, y, z
        )
    else:
        return response.json()


# https://github.com/elitedangereuse/edgis/blob/c7f98f266a7536530232a9946268bbb0dd77b63c/api/systems.py#L1078
# https://edgis.elitedangereuse.fr/coords?q=<url_encoded_system_name>
fetch_coords_uri: str = r"https://edgis.elitedangereuse.fr/coords"


def fetch_system_info(system_name: str) -> dict[str, Any] | None:
    logger.debug("Fetching system info for system=%s", system_name)
    response = None
    try:
        # The API expects the system name under the `q` query parameter.
        response = requests.get(fetch_coords_uri, params={"q": system_name})
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Failed to fetch system info for system=%s", system_name)
        return None
    else:
        return response.json()


if __name__ == "__main__":
    main()
