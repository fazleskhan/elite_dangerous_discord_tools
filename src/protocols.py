from __future__ import annotations

from pathlib import Path
from typing import Any, Awaitable, Callable, Protocol, Sequence

from defaults import DEFAULT_INIT_DIR

SystemInfo = dict[str, Any]
FetchInfoFn = Callable[[str], SystemInfo | None]
FetchSystemInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[..., list[SystemInfo] | None]
DistanceFn = Callable[[str, str], float]
ProgressFn = Callable[[str], None]


class IDatasource(Protocol):
    def init_datasource(self, import_dir: str | Path = DEFAULT_INIT_DIR) -> None: ...
    def get_all_systems(self) -> list[SystemInfo]: ...
    def get_system(self, system_name: str) -> SystemInfo | None: ...
    def insert_system(self, system_info: SystemInfo) -> None: ...
    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None: ...


class ICache(Protocol):
    def find_system_info(self, system_name: str) -> SystemInfo | None: ...
    def find_system_neighbors(
        self, system_info: SystemInfo
    ) -> list[SystemInfo] | None: ...


class ILogger(Protocol):
    def trace(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def debug(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def info(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def warn(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def warning(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def error(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def exception(self, message: str, *args: Any, **kwargs: Any) -> None: ...
    def opt(self, *args: Any, **kwargs: Any) -> Any: ...


class IGis(Protocol):
    def fetch_system_info(self, system_name: str) -> SystemInfo | None: ...
    def fetch_neighbors(
        self, x: float | int, y: float | int, z: float | int
    ) -> list[SystemInfo] | None: ...


class IRouteService(Protocol):
    def init_datasource(
        self, import_dir: str | Path = DEFAULT_INIT_DIR
    ) -> None | Awaitable[None]: ...
    def get_system_info(self, system_name: str) -> Any | Awaitable[Any]: ...
    def get_all_system_names(self) -> Sequence[str] | Awaitable[Sequence[str]]: ...
    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float | Awaitable[float]: ...
    def path(
        self,
        initial_system_name: str,
        destination_system_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> Sequence[str] | None | Awaitable[Sequence[str] | None]: ...
    def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> Sequence[str] | Awaitable[Sequence[str]]: ...


class IBfs(Protocol):
    def travel(
        self,
        start_name: str,
        destination_name: str,
        max_count: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None: ...


class IBulkLoad(Protocol):
    def load(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]: ...


class IInitDatasource(Protocol):
    def run(self, import_dir: str | Path = DEFAULT_INIT_DIR) -> None: ...


class IGetSystemInfo(Protocol):
    def run(self, system_name: str) -> SystemInfo | None: ...


class IGetAllSystemNames(Protocol):
    def run(self) -> list[str]: ...


class IPathService(Protocol):
    async def run(
        self,
        initial_system_name: str,
        destination_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None: ...


class ICalcSystemsDistance(Protocol):
    def run(self, system_name_one: str, system_name_two: str) -> float: ...


DatasourceProtocol = IDatasource
CacheProtocol = ICache
LoggingProtocol = ILogger
GisProtocol = IGis
RouteServiceProtocol = IRouteService
BfsProtocol = IBfs
BulkLoadProtocol = IBulkLoad
InitDatasourceProtocol = IInitDatasource
GetSystemInfoProtocol = IGetSystemInfo
GetAllSystemNamesProtocol = IGetAllSystemNames
PathProtocol = IPathService
CalcSystemsDistanceProtocol = ICalcSystemsDistance
