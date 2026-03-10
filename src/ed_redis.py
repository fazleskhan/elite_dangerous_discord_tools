import asyncio
import atexit
import json
import os
import threading
from typing import Any
from urllib.parse import urlparse

import psutil
from redis import asyncio as redis

from ed_protocols import LoggingProtocol, SystemInfo
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


def main() -> None: ...


class EDRedis:
    @staticmethod
    def create(
        logging_utils: LoggingProtocol,
        datasource_name: str | None = None,
        redis_url: str | None = None,
        max_connections: int | None = None,
    ) -> "EDRedis":
        # Namespace defaults to REDIS_APP_NAME so multiple apps can share Redis.
        resolved_redis_url = (
            redis_url if redis_url is not None else EDRedis._resolve_redis_url()
        )
        return EDRedis(
            datasource_name or os.getenv(redis_app_name_env, default_redis_store_name),
            redis_url=resolved_redis_url,
            logging_utils=logging_utils,
            max_connections=max_connections,
        )

    def __init__(
        self,
        datasource_name: str,
        redis_url: str,
        logging_utils: LoggingProtocol,
        max_connections: int,
    ):
        if redis_url is None:
            raise ValueError("Redis URL of type str is a required argument")
        else:
            self._redis_url = redis_url
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        else:
            self.logger = logging_utils
        if datasource_name is None:
            raise ValueError("datasource_name of type str is required")
        else:
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

    # Synchronous helper used by import scripts and CLI commands.
    def init_datasource(self, import_dir: str = default_init_dir) -> None:
        self.import_datasource(import_dir)

    # Import/export entrypoints are sync by design for CLI/script usage.
    def import_datasource(self, import_dir: str) -> None:
        if not os.path.isdir(import_dir):
            raise FileNotFoundError(f"Import directory does not exist: {import_dir}")
        json_filenames = sorted(
            filename
            for filename in os.listdir(import_dir)
            if filename.endswith(json_extension)
        )
        self.logger.info(
            "Importing Redis datasource from {} JSON files in {}",
            len(json_filenames),
            import_dir,
        )
        for filename in json_filenames:
            json_path = os.path.join(import_dir, filename)
            with open(json_path, encoding="utf-8") as json_file:
                payload = json.load(json_file)

            records = payload if isinstance(payload, list) else [payload]
            for record in records:
                if isinstance(record, dict):
                    self.insert_system(record)

    # Import/export entrypoints are sync by design for CLI/script usage.
    def export_datasource(self, export_dir: str) -> None:
        os.makedirs(export_dir, exist_ok=True)
        systems = self.get_all_systems()
        for system in systems:
            system_name = system.get(system_info_name_field)
            if not isinstance(system_name, str) or not system_name:
                continue
            full_system = self.get_system(system_name)
            if full_system is None:
                continue
            output_path = os.path.join(
                export_dir,
                f"{self._safe_filename(system_name)}{json_extension}",
            )
            with open(output_path, "w", encoding="utf-8") as file_handle:
                json.dump(
                    full_system,
                    file_handle,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                )
                file_handle.write("\n")

    def _safe_filename(self, system_name: str) -> str:
        return "".join(
            (
                character
                if character.isalnum() or character in (" ", "-", "_", ".")
                else "_"
            )
            for character in system_name
        ).strip()

    @staticmethod
    def _default_max_connections() -> int:
        physical_cores = psutil.cpu_count(logical=False)
        if physical_cores is None or physical_cores < 1:
            return 1
        return physical_cores

    @staticmethod
    def _resolve_redis_url(redis_url: str | None = None) -> str:
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
                output[value_key] = asyncio.run(coro)
            except BaseException as exc:
                error[value_key] = exc

        worker = threading.Thread(target=_worker, daemon=True)
        worker.start()
        worker.join()

        if value_key in error:
            raise error[value_key]

        return output.get(value_key)

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
        # Namespace keys by app name so multiple bots can share one Redis safely.
        return f"{self.datasource_name}:{system_field}:{system_name}"

    @property
    def _systems_set_key(self) -> str:
        return f"{self.datasource_name}:{systems_field}"

    async def _insert_system_async(self, system_info: SystemInfo) -> None:
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
        self._ensure_open()
        with self._write_lock:
            self._run_async(self._insert_system_async(system_info))

    def get_system(self, system_name: str) -> SystemInfo | None:
        try:
            return self._run_async(self._get_system_async(system_name))
        except Exception:
            self.logger.exception("Lookup failed for system={}", system_name)
            return None

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None:
        self._ensure_open()
        with self._write_lock:
            self._run_async(self._add_neighbors_async(system_info, new_neighbors))

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
