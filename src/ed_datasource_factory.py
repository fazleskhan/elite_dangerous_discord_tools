"""IoC helpers for datasource/cache/route service composition."""

import os
from typing import Any

from dotenv import load_dotenv

from constants import (
    datasource_type_env,
    redis_name,
    tinydb_name,
)
from ed_protocols import DatasourceProtocol, LoggingProtocol


class EDDatasourceFactory:
    """Factory for selecting concrete datasource implementations."""

    def __init__(self, logger: LoggingProtocol) -> None:
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self._logger = logger

    def create_datasource(
        self,
        *,
        datasource_name: str | None = None,
        datasource_type: str | None = None,
    ) -> DatasourceProtocol:
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
    if logger is None:
        raise ValueError("logger must not be null")
    factory = EDDatasourceFactory(logger=logger)
    return factory.create_datasource(
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )
