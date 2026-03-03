from __future__ import annotations

from tinydb import TinyDB
from typing import Any


class AIOTinyDB:
    """Minimal async-compatible wrapper around TinyDB.

    This allows code paths that expect aiotinydb to run in environments
    where the external package is unavailable.
    """

    def __init__(self, path: str):
        self._path = path
        self._db: TinyDB | None = None

    async def __aenter__(self) -> "AIOTinyDB":
        self._db = TinyDB(self._path)
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if self._db is not None:
            self._db.close()
            self._db = None

    def _require_db(self) -> TinyDB:
        if self._db is None:
            raise RuntimeError("AIOTinyDB must be used within 'async with'")
        return self._db

    async def contains(self, cond: Any) -> bool:
        return self._require_db().contains(cond)

    async def insert(self, document: dict[str, Any]) -> int:
        return self._require_db().insert(document)

    async def get(self, cond: Any) -> dict[str, Any] | None:
        return self._require_db().get(cond)

    async def update(self, fields: dict[str, Any], cond: Any) -> list[int]:
        return self._require_db().update(fields, cond)

    async def all(self) -> list[dict[str, Any]]:
        return self._require_db().all()
