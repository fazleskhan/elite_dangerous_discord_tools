"""IoC helpers for datasource/cache/route service composition."""

import os
from typing import Any

from dotenv import load_dotenv

from ed_constants import (
    datasource_type_env,
    redis_name,
    tinydb_name,
)
from ed_logging_utils import EDLoggingUtils
from ed_protocols import DatasourceProtocol, LoggingProtocol


def main() -> None: ...


class EDDatasourceFactory:
    """Factory for selecting concrete datasource implementations."""

    def __init__(self, logging_utils: LoggingProtocol) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        self._logging_utils = logging_utils

    @staticmethod
    def create(logging_utils: LoggingProtocol) -> "EDDatasourceFactory":
        return EDDatasourceFactory(logging_utils)

    def create_datasource(
        self,
        *,
        datasource_name: str | None = None,
        datasource_type: str | None = None,
    ) -> DatasourceProtocol:
        load_dotenv()
        resolved_type = resolve_datasource_type(datasource_type)
        if resolved_type == tinydb_name:
            from ed_tinydb import EDTinyDB

            return EDTinyDB.create(
                datasource_name=datasource_name,
                logging_utils=self._logging_utils,
            )

        from ed_redis import EDRedis

        return EDRedis.create(
            datasource_name=datasource_name,
            logging_utils=self._logging_utils,
        )


def resolve_datasource_type(datasource_type: str | None = None) -> str:
    # Explicit arg wins, then env, then tinydb default.
    resolved = (
        (
            datasource_type
            or os.getenv(datasource_type_env)
            or tinydb_name
        )
        .strip()
        .lower()
    )
    if resolved not in {tinydb_name, redis_name}:
        raise ValueError(
            "Invalid DATASOURCE_TYPE value. Supported values are 'tinydb' and 'redis'."
        )
    return resolved


def create_datasource(
    datasource_name: str | None = None, datasource_type: str | None = None
) -> Any:
    factory = EDDatasourceFactory.create(
        logging_utils=EDLoggingUtils(),
    )
    return factory.create_datasource(
        datasource_name=datasource_name,
        datasource_type=datasource_type,
    )


if __name__ == "__main__":
    main()
