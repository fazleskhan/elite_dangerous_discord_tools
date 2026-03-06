"""Compatibility shim for callers importing `db`."""

import os

from ed_redis import EDRedis
from ed_tinydb import EDTinyDB, SystemInfo

DATASTORE_TYPE = os.getenv("DATASTORE_TYPE", "tinydb").strip().lower()

if DATASTORE_TYPE == "tinydb":
    DB = EDTinyDB
elif DATASTORE_TYPE == "redis":
    if not os.getenv("REDIS_URL"):
        raise ValueError(
            "REDIS_URL is required when DATASTORE_TYPE is set to 'redis'"
        )
    DB = EDRedis
else:
    raise ValueError(
        "Invalid DATASTORE_TYPE value. Supported values are 'tinydb' and 'redis'."
    )


def main() -> None: ...


if __name__ == "__main__":
    main()
