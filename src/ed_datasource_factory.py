"""IoC helpers for datasource/cache/route service composition."""

import os
from typing import Any

from dotenv import load_dotenv

from ed_constants import (
    datasource_type_env,
    redis_name,
    tinydb_name,
)
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDDatasourceFactory:
    """Factory for selecting concrete datasource implementations."""

    def __init__(self, logger: LoggingProtocol) -> None:
        """Store the shared logger used during datasource composition.

        Datasource construction is a central wiring step, so the factory keeps
        the logger close at hand for whichever backend implementation is
        selected.
        """
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger

    def create_datasource(
        self,
        *,
        datasource_name: str | None = None,
        datasource_type: str | None = None,
    ) -> DatasourceProtocol:
        """Instantiate the configured datasource backend.

        The method loads environment configuration, resolves which backend the
        application should use, and constructs either TinyDB or Redis with the
        shared logger and any optional datasource-name override.
        """
        # Ensure .env-backed datasource settings are available in CLI/runtime.
        load_dotenv()
        resolved_type = resolve_datasource_type(datasource_type)
        if resolved_type == tinydb_name:
            from ed_tinydb import EDTinyDB

            return EDTinyDB.create(
                datasource_name=datasource_name,
                logger=self._logger,
            )

        from ed_redis import EDRedis

        return EDRedis.create(
            datasource_name=datasource_name,
            logger=self._logger,
        )


def resolve_datasource_type(datasource_type: str | None = None) -> str:
    """Resolve and validate the datasource backend name.

    Resolution follows the project's precedence order of explicit argument,
    environment variable, and TinyDB default, then normalizes the result and
    rejects unsupported backend names early.
    """
    # Resolution order: explicit arg -> env var -> tinydb default.
    resolved = (
        (datasource_type or os.getenv(datasource_type_env) or tinydb_name)
        .strip()
        .lower()
    )
    if resolved not in {tinydb_name, redis_name}:
        raise ValueError(
            "Invalid DATASOURCE_TYPE value. Supported values are 'tinydb' and 'redis'."
        )
    return resolved


def create_datasource(
    datasource_name: str | None = None,
    datasource_type: str | None = None,
    logger: LoggingProtocol | None = None,
) -> Any:
    """Create a datasource through the shared factory helper.

    This convenience wrapper keeps call sites concise while routing backend
    selection and validation through `EDDatasourceFactory`.
    """
    if logger is None:
        raise ValueError("logger must not be null")
    return EDDatasourceFactory(logger=logger).create_datasource(
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )
