from __future__ import annotations

import asyncio
import threading
from typing import Any


def run_async_from_sync(coro: Any, *, value_key: str) -> Any:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

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
