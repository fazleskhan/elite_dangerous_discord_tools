import atexit
import inspect
import json
import os
import threading
from typing import Any, cast
from collections.abc import Awaitable
from urllib.parse import urlparse

import psutil
from redis import asyncio as redis

from ed_datasource_json_io import (
    export_json_records,
    import_json_records,
    safe_filename,
)
from ed_protocols import LoggingProtocol, SystemInfo
from ed_sync_async_bridge import run_async_from_sync
from ed_constants import (
    default_init_dir,
    default_redis_store_name,
    json_extension,
    redis_app_name_env,
    redis_max_connections_env,
    redis_name,
    redis_scheme,
    redis_url_env,
    rediss_scheme,
    system_field,
    system_info_name_field,
    system_info_neighbors_field,
    systems_field,
    unix_scheme,
    value_key,
)

"""Redis persistence helpers for cached system records."""


class EDRedis:
    """Redis-backed datasource for cached system records.

    The datasource stores each system payload as a namespaced Redis key, tracks
    all known system names in a companion set for enumeration, and bridges its
    async Redis client operations back into the project's synchronous API.
    """

    @staticmethod
    def create(
        logger: LoggingProtocol,
        datasource_name: str | None = None,
        redis_url: str | None = None,
        max_connections: int | None = None,
    ) -> "EDRedis":
        """Build a Redis datasource using defaults when options are omitted.

        The factory resolves the Redis URL, application namespace, and
        connection-pool size from explicit input or environment variables before
        constructing the datasource instance.
        """
        resolved_redis_url = (
            redis_url if redis_url is not None else EDRedis._resolve_redis_url()
        )
        resolved_datasource_name = datasource_name
        if resolved_datasource_name is None:
            resolved_datasource_name = (
                os.getenv(redis_app_name_env) or default_redis_store_name
            )
        resolved_max_connections = max_connections
        if resolved_max_connections is None:
            resolved_max_connections = int(
                os.getenv(
                    redis_max_connections_env,
                    str(EDRedis._default_max_connections()),
                )
            )
        return EDRedis(
            resolved_datasource_name,
            redis_url=resolved_redis_url,
            logger=logger,
            max_connections=resolved_max_connections,
        )

    def __init__(
        self,
        datasource_name: str,
        redis_url: str,
        logger: LoggingProtocol,
        max_connections: int | None,
    ):
        """Initialize Redis connection settings, locks, and shutdown behavior.

        The constructor validates the required inputs, stores the Redis
        connection configuration, and registers a shutdown hook so the datasource
        can mark itself closed when the process exits.
        """
        if redis_url is None:
            raise ValueError("Redis URL of type str is a required argument")
        self._redis_url = redis_url
        if logger is None:
            raise ValueError("logger of type LoggingProtocol is required")
        self.logger = logger
        if datasource_name is None:
            raise ValueError("datasource_name of type str is required")
        self.datasource_name = datasource_name

        self._write_lock = threading.Lock()
        self._close_lock = threading.Lock()
        self._closed = False
        self._max_connections = (
            max_connections
            if max_connections is not None
            else int(
                os.getenv(
                    redis_max_connections_env,
                    str(self._default_max_connections()),
                )
            )
        )
        atexit.register(self.close)
        self.logger.info("Redis backend: {}", redis_name)

    def init_datasource(
        self, import_dir: str | os.PathLike[str] = default_init_dir
    ) -> None:
        """Initialize the Redis datasource from a seed directory.

        Redis requires no schema setup beyond being reachable, so initialization
        simply delegates to the JSON import flow.
        """
        self.import_datasource(import_dir)

    def import_datasource(self, import_dir: str | os.PathLike[str]) -> None:
        """Import per-system JSON files into Redis.

        The method delegates directory walking and JSON decoding to the shared
        import helper and inserts each decoded record through this datasource.
        """
        import_json_records(
            import_dir=import_dir,
            json_extension=json_extension,
            logger=self.logger,
            log_message="Importing Redis datasource from {} JSON files in {}",
            insert_record=self.insert_system,
        )

    def export_datasource(self, export_dir: str) -> None:
        """Export all stored Redis systems into JSON files.

        The method delegates file creation to the shared export helper and
        resolves each listed system through the datasource's lookup method.
        """
        export_json_records(
            export_dir=export_dir,
            json_extension=json_extension,
            systems=self.get_all_systems(),
            system_name_field=system_info_name_field,
            get_full_system=self.get_system,
        )

    def _safe_filename(self, system_name: str) -> str:
        """Return a filesystem-safe filename derived from a system name.

        This thin wrapper preserves the datasource's older helper surface while
        delegating the actual sanitization to the shared JSON I/O helper.
        """
        return safe_filename(system_name)

    @staticmethod
    def _default_max_connections() -> int:
        """Return the preferred Redis connection-pool size.

        The project ties the default pool size to the number of physical CPU
        cores so concurrent Redis work has a practical upper bound without
        oversubscribing connections.
        """
        physical_cores = psutil.cpu_count(logical=False)
        if physical_cores is None or physical_cores < 1:
            return 1
        return physical_cores

    @staticmethod
    def _resolve_redis_url(redis_url: str | None = None) -> str:
        """Resolve and validate the Redis connection URL.

        The helper pulls the URL from the explicit argument or environment,
        verifies that it uses a supported scheme, and ensures host requirements
        are met for TCP-based Redis connections.
        """
        final_redis_url = redis_url or os.getenv(redis_url_env)
        if not final_redis_url:
            raise ValueError(
                "REDIS_URL is required when DATASOURCE_TYPE is set to 'redis'"
            )

        parsed = urlparse(final_redis_url)
        if parsed.scheme not in {
            redis_scheme,
            rediss_scheme,
            unix_scheme,
        }:
            raise ValueError(
                "REDIS_URL must use one of these schemes: redis, rediss, unix"
            )
        if parsed.scheme in {redis_scheme, rediss_scheme} and not parsed.hostname:
            raise ValueError("REDIS_URL must include a host for redis/rediss schemes")

        return final_redis_url

    def _run_async(self, coro: Any) -> Any:
        """Execute a Redis coroutine from the synchronous datasource API.

        The helper first verifies the datasource has not been closed and then
        uses the shared sync/async bridge to wait for the coroutine result.
        """
        self._ensure_open()
        return run_async_from_sync(coro, value_key=value_key)

    def _new_client(self) -> Any:
        """Create a new Redis client using the configured connection settings.

        The datasource uses short-lived clients for each operation so this
        helper centralizes the client construction details.
        """
        return redis.from_url(
            self._redis_url,
            decode_responses=True,
            max_connections=self._max_connections,
        )

    async def _close_client_async(self, client: Any) -> None:
        """Close a Redis client regardless of its close API shape.

        Different Redis client versions expose either `aclose` or `close`, so
        the helper checks both forms and awaits the result when necessary.
        """
        # Prefer async close when available; keep a compatibility path for
        # clients exposing only sync `close`.
        close_fn = getattr(client, "aclose", None)
        if callable(close_fn):
            await cast(Awaitable[Any], close_fn())
            return

        legacy_close = getattr(client, "close", None)
        if callable(legacy_close):
            close_result = legacy_close()
            if inspect.isawaitable(close_result):
                await close_result

    def _ensure_open(self) -> None:
        """Raise if the datasource has already been closed.

        Public operations call this guard before touching Redis so callers get a
        clear failure instead of undefined behavior after shutdown.
        """
        if self._closed:
            raise RuntimeError("Redis client is closed")

    def _system_key(self, system_name: str) -> str:
        """Return the namespaced Redis key for one system payload.

        The application namespaces keys by datasource name so multiple
        deployments can share one Redis instance without clobbering each other.
        """
        # Namespace keys by app name so multiple bots can share one Redis safely.
        return f"{self.datasource_name}:{system_field}:{system_name}"

    @property
    def _systems_set_key(self) -> str:
        """Return the Redis set key that tracks all known system names.

        The datasource stores names in a companion set so it can enumerate
        systems efficiently without scanning every namespaced key in Redis.
        """
        # Track known system names separately so Redis can enumerate records
        # without scanning every namespaced key in the database.
        return f"{self.datasource_name}:{systems_field}"

    async def _insert_system_async(self, system_info: SystemInfo) -> None:
        """Insert one system payload into Redis if it is not already stored.

        The helper checks the namespaced system key, writes the JSON payload on
        misses, and adds the system name to the companion set used for full
        enumeration.
        """
        system_name = system_info[system_info_name_field]
        system_key = self._system_key(system_name)
        client = self._new_client()
        try:
            if await client.exists(system_key):
                self.logger.debug(
                    "Skipped duplicate system insert for system={}", system_name
                )
                return

            await client.set(system_key, json.dumps(system_info))
            await client.sadd(self._systems_set_key, system_name)
            self.logger.debug("Inserted system={}", system_name)
        finally:
            await self._close_client_async(client)

    async def _get_system_async(self, system_name: str) -> SystemInfo | None:
        """Return one stored system payload from Redis.

        The helper loads the namespaced Redis key, decodes the stored JSON when
        present, and returns `None` for normal cache misses.
        """
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
    ) -> None:
        """Replace the stored neighbor list for a system payload in Redis.

        The helper reloads the stored JSON payload, updates its neighbor list,
        and writes the full payload back to the namespaced Redis key.
        """
        system_name = system_info[system_info_name_field]
        system_key = self._system_key(system_name)
        client = self._new_client()
        try:
            current = await client.get(system_key)
            if current is None:
                self.logger.debug(
                    "Updated neighbors for system={} updated_rows=0", system_name
                )
                return

            system_payload = json.loads(current)
            system_payload[system_info_neighbors_field] = new_neighbors
            await client.set(system_key, json.dumps(system_payload))
            self.logger.debug(
                "Updated neighbors for system={} updated_rows={}",
                system_name,
                1,
            )
        finally:
            await self._close_client_async(client)

    async def _get_all_systems_async(self) -> list[SystemInfo]:
        """Return every stored system payload from Redis.

        The helper uses the companion system-name set to build the key list,
        performs a bulk `mget`, and decodes each present payload into a system
        record.
        """
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

    def insert_system(self, system_info: SystemInfo) -> None:
        """Persist one system payload through the synchronous Redis API.

        The method serializes writes under a lock and bridges the underlying
        async insert helper into the caller-facing synchronous surface.
        """
        self._ensure_open()
        with self._write_lock:
            self._run_async(self._insert_system_async(system_info))

    def get_system(self, system_name: str) -> SystemInfo | None:
        """Return one stored system payload, shielding callers from backend errors.

        The synchronous wrapper bridges the async lookup helper and logs then
        returns `None` if Redis raises unexpectedly.
        """
        try:
            return self._run_async(self._get_system_async(system_name))
        except Exception:
            self.logger.exception("Lookup failed for system={}", system_name)
            return None

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None:
        """Persist neighbor data for a stored system.

        The method serializes the write under a lock and bridges the underlying
        async neighbor-update helper back into the synchronous API.
        """
        self._ensure_open()
        with self._write_lock:
            self._run_async(self._add_neighbors_async(system_info, new_neighbors))

    def get_all_systems(self) -> list[SystemInfo]:
        """Return every stored system payload through the synchronous API.

        The method verifies the datasource is still open and bridges the async
        Redis scan into the synchronous caller interface.
        """
        self._ensure_open()
        return self._run_async(self._get_all_systems_async())

    def close(self) -> None:
        """Mark the datasource closed so future Redis operations fail fast.

        The datasource creates short-lived Redis clients per operation, so
        closing simply flips the shared closed flag under a lock.
        """
        with self._close_lock:
            if self._closed:
                return
            self._closed = True
