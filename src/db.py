"""Compatibility shim for callers importing `db`."""

import os

from typing import Any

DATASTORE_TYPE = os.getenv("DATASTORE_TYPE", "tinydb").strip().lower()
SystemInfo = dict[str, Any]

if DATASTORE_TYPE == "tinydb":
    from ed_tinydb import EDTinyDB

    DB = EDTinyDB
elif DATASTORE_TYPE == "redis":
    if not os.getenv("REDIS_URL"):
        raise ValueError(
            "REDIS_URL is required when DATASTORE_TYPE is set to 'redis'"
        )
    from ed_redis import EDRedis

    DB = EDRedis
else:
    raise ValueError(
        "Invalid DATASTORE_TYPE value. Supported values are 'tinydb' and 'redis'."
    )


def main() -> None: ...


if __name__ == "__main__":
    main()
