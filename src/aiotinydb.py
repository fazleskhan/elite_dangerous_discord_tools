from __future__ import annotations

from tinydb import TinyDB
from tinydb.storages import JSONStorage
from tinydb_smartcache import SmartCacheTable
from typing import Any, cast


class SmartCacheTinyDB(TinyDB):
    # Swap TinyDB's default table with SmartCache's query-cache table.
    table_class = SmartCacheTable


class AIOTinyDB:
    """Minimal async-compatible wrapper around TinyDB.

    This allows code paths that expect aiotinydb to run in environments
    where the external package is unavailable.
    """

    def __init__(self, path: str):
        self._path = path
        self._db: TinyDB | None = None

    async def __aenter__(self) -> "AIOTinyDB":
        # Use SmartCache table implementation for cached query results.
        self._db = SmartCacheTinyDB(self._path, storage=JSONStorage)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def _require_db(self) -> TinyDB:
        # Central guard so async wrapper methods fail fast if misused.
        if self._db is None:
            raise RuntimeError("AIOTinyDB must be used within 'async with'")
        return self._db

    async def contains(self, cond: Any) -> bool:
        return self._require_db().contains(cond)

    async def insert(self, document: dict[str, Any]) -> int:
        return self._require_db().insert(document)

    async def get(self, cond: Any) -> dict[str, Any] | None:
        return cast(dict[str, Any] | None, self._require_db().get(cond))

    async def update(self, fields: dict[str, Any], cond: Any) -> list[int]:
        return self._require_db().update(fields, cond)

    async def all(self) -> list[dict[str, Any]]:
        return cast(list[dict[str, Any]], self._require_db().all())
