import asyncio
import atexit
import json
import os
import threading
from typing import Any
from urllib.parse import urlparse

import psutil
from loguru import logger
from redis import asyncio as redis

import constants

"""Redis persistence helpers for cached system records."""

SystemInfo = dict[str, Any]


def main() -> None: ...


class EDRedis:
    def __init__(self, database_name: str, redis_url: str | None = None):
        self._app_name = os.getenv("REDIS_APP_NAME", "eddt")
        self._write_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._closed = False
        self.logger = logger
        self._redis_url = self._resolve_redis_url(redis_url)
        self._max_connections = int(
            os.getenv("REDIS_MAX_CONNECTIONS", str(self._default_max_connections()))
        )
        atexit.register(self.close)
        self.logger.info("DB backend: redis")

    @staticmethod
    def _default_max_connections() -> int:
        physical_cores = psutil.cpu_count(logical=False)
        if physical_cores is None or physical_cores < 1:
            return 1
        return physical_cores

    @staticmethod
    def _resolve_redis_url(redis_url: str | None) -> str:
        final_redis_url = redis_url or os.getenv("REDIS_URL")
        if not final_redis_url:
            raise ValueError(
                "REDIS_URL is required when DATASTORE_TYPE is set to 'redis'"
            )

        parsed = urlparse(final_redis_url)
        if parsed.scheme not in {"redis", "rediss", "unix"}:
            raise ValueError(
                "REDIS_URL must use one of these schemes: redis, rediss, unix"
            )
        if parsed.scheme in {"redis", "rediss"} and not parsed.hostname:
            raise ValueError("REDIS_URL must include a host for redis/rediss schemes")

        return final_redis_url

    def _run_async(self, coro: Any) -> Any:
        self._ensure_open()
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            # Standard sync call path: create a short-lived loop for this op.
            return asyncio.run(coro)

        output: dict[str, Any] = {}
        error: dict[str, BaseException] = {}

        def _worker() -> None:
            try:
                # If caller is already inside an event loop, run in a helper
                # thread so sync methods can still block on completion.
                output["value"] = asyncio.run(coro)
            except BaseException as exc:
                error["value"] = exc

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        worker.join()

        if "value" in error:
            raise error["value"]

        return output.get("value")

    def _new_client(self) -> Any:
        # Each client uses redis-py's internal connection pool; max pool size is
        # bounded to avoid unbounded socket growth.
        return redis.from_url(
            self._redis_url,
            decode_responses=True,
            max_connections=self._max_connections,
        )

    async def _close_client_async(self, client: Any) -> None:
        # Prefer async close when available; keep a compatibility path for
        # clients exposing only sync `close`.
        close_fn = getattr(client, "aclose", None)
        if callable(close_fn):
            await close_fn()
            return

        legacy_close = getattr(client, "close", None)
        if callable(legacy_close):
            close_result = legacy_close()
            if asyncio.iscoroutine(close_result):
                await close_result

    def _ensure_open(self) -> None:
        if self._closed:
            raise RuntimeError("Redis client is closed")

    def _system_key(self, system_name: str) -> str:
        return f"{self._app_name}:system:{system_name}"

    @property
    def _systems_set_key(self) -> str:
        return f"{self._app_name}:systems"

    @property
    def _doc_id_counter_key(self) -> str:
        return f"{self._app_name}:doc_id_counter"

    @property
    def _doc_ids_hash_key(self) -> str:
        return f"{self._app_name}:doc_ids"

    async def _insert_system_async(self, system_info: SystemInfo) -> int | None:
        system_name = system_info[constants.system_info_name_field]
        system_key = self._system_key(system_name)
        client = self._new_client()
        try:
            if await client.exists(system_key):
                self.logger.debug(
                    "Skipped duplicate system insert for system={}", system_name
                )
                return None

            inserted_id = int(await client.incr(self._doc_id_counter_key))
            await client.set(system_key, json.dumps(system_info))
            await client.sadd(self._systems_set_key, system_name)
            await client.hset(self._doc_ids_hash_key, system_name, inserted_id)
            self.logger.debug("Inserted system={} doc_id={}", system_name, inserted_id)
            return inserted_id
        finally:
            await self._close_client_async(client)

    async def _get_system_async(self, system_name: str) -> SystemInfo | None:
        client = self._new_client()
        try:
            result = await client.get(self._system_key(system_name))
            if result is None:
                self.logger.debug("Lookup system={} found=False", system_name)
                return None

            decoded = json.loads(result)
            self.logger.debug("Lookup system={} found=True", system_name)
            return decoded
        finally:
            await self._close_client_async(client)

    async def _add_neighbors_async(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> list[int]:
        system_name = system_info[constants.system_info_name_field]
        system_key = self._system_key(system_name)
        client = self._new_client()
        try:
            current = await client.get(system_key)
            if current is None:
                self.logger.debug(
                    "Updated neighbors for system={} updated_rows=0", system_name
                )
                return []

            system_payload = json.loads(current)
            system_payload[constants.system_info_neighbors_field] = new_neighbors
            await client.set(system_key, json.dumps(system_payload))
            raw_doc_id = await client.hget(self._doc_ids_hash_key, system_name)
            if raw_doc_id is None:
                self.logger.debug(
                    "Updated neighbors for system={} updated_rows=0", system_name
                )
                return []

            updated = [int(raw_doc_id)]
            self.logger.debug(
                "Updated neighbors for system={} updated_rows={}",
                system_name,
                len(updated),
            )
            return updated
        finally:
            await self._close_client_async(client)

    async def _get_all_systems_async(self) -> list[SystemInfo]:
        client = self._new_client()
        try:
            system_names = sorted(await client.smembers(self._systems_set_key))
            if not system_names:
                self.logger.debug("Loaded all systems count=0")
                return []

            payloads = await client.mget(
                [self._system_key(name) for name in system_names]
            )
            systems = [
                json.loads(payload) for payload in payloads if payload is not None
            ]
            self.logger.debug("Loaded all systems count={}", len(systems))
            return systems
        finally:
            await self._close_client_async(client)

    def insert_system(self, system_info: SystemInfo) -> int | None:
        self._ensure_open()
        with self._write_lock:
            return self._run_async(self._insert_system_async(system_info))

    def get_system(self, system_name: str) -> SystemInfo | None:
        try:
            return self._run_async(self._get_system_async(system_name))
        except Exception:
            self.logger.exception("Lookup failed for system={}", system_name)
            return None

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> list[int]:
        self._ensure_open()
        with self._write_lock:
            return self._run_async(
                self._add_neighbors_async(system_info, new_neighbors)
            )

    def get_all_systems(self) -> list[SystemInfo]:
        self._ensure_open()
        return self._run_async(self._get_all_systems_async())

    def close(self) -> None:
        with self._close_lock:
            if self._closed:
                return
            self._closed = True


if __name__ == "__main__":
    main()
