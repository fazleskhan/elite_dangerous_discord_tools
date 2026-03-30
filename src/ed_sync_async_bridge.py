from __future__ import annotations

import asyncio
import threading
from typing import Any


def run_async_from_sync(coro: Any, *, value_key: str) -> Any:
    """Execute a coroutine from synchronous code and return its result.

    The helper uses `asyncio.run` when no loop is active and falls back to a
    worker thread when the caller is already inside an event loop, allowing
    synchronous APIs to safely wait on async implementations in both contexts.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    # When a caller is already inside an event loop, hop to a worker thread so
    # the synchronous API can still wait for the coroutine result safely.
    output: dict[str, Any] = {}
    error: dict[str, BaseException] = {}

    def _worker() -> None:
        try:
            output[value_key] = asyncio.run(coro)
        except BaseException as exc:
            error[value_key] = exc

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join()

    if value_key in error:
        raise error[value_key]

    return output.get(value_key)
