import threading
from typing import Any


class ThreadSafeLogger:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.calls: list[tuple[str, str, tuple[Any, ...]]] = []

    def _record(self, level: str, message: str, args: tuple[Any, ...]) -> None:
        with self._lock:
            self.calls.append((level, message, args))

    def debug(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("debug", message, args)

    def info(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("info", message, args)

    def warning(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("warning", message, args)

    def error(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("error", message, args)

    def exception(self, message: str, *args: Any, **_kwargs: Any) -> None:
        self._record("exception", message, args)

    def opt(self, *args: Any, **kwargs: Any) -> "ThreadSafeLogger":
        return self

    def messages(self, level: str) -> list[tuple[str, tuple[Any, ...]]]:
        with self._lock:
            return [
                (message, args)
                for call_level, message, args in self.calls
                if call_level == level
            ]
