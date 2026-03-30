from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol
from collections.abc import Awaitable, Callable, Sequence

from ed_defaults import DEFAULT_INIT_DIR

SystemInfo = dict[str, Any]
FetchInfoFn = Callable[[str], SystemInfo | None]
FetchSystemInfoFn = Callable[[str], SystemInfo | None]
FetchNeighborsFn = Callable[..., list[SystemInfo] | None]
DistanceFn = Callable[[str, str], float]
ProgressFn = Callable[[str], None]


class IDatasource(Protocol):
    """Protocol for datasource backends that persist system records.

    Implementations provide initialization, single-record access, full scans,
    inserts, and neighbor updates so the rest of the application can remain
    storage-agnostic.
    """

    def init_datasource(self, import_dir: str | Path = DEFAULT_INIT_DIR) -> None:
        """Initialize the datasource from a seed import directory.

        Implementations typically create any required storage structures and
        then load initial records from the supplied filesystem path.
        """
        ...

    def get_all_systems(self) -> list[SystemInfo]:
        """Return every persisted system payload.

        Implementations provide a full scan of stored system records so higher
        layers can inspect or export the complete cache contents.
        """
        ...

    def get_system(self, system_name: str) -> SystemInfo | None:
        """Return the persisted payload for one system name.

        Implementations should return `None` when the system is absent rather
        than raising for a normal cache miss.
        """
        ...

    def insert_system(self, system_info: SystemInfo) -> None:
        """Persist one system payload into the datasource.

        Implementations store the provided system record using the backend's
        native persistence model and deduplication behavior.
        """
        ...

    def add_neighbors(
        self, system_info: SystemInfo, new_neighbors: list[SystemInfo]
    ) -> None:
        """Attach or update neighbor data for an existing system record.

        Implementations merge the provided neighbor list into the stored system
        payload so later lookups can reuse cached neighbor information.
        """
        ...


class ICache(Protocol):
    """Protocol for cache layers that wrap system and neighbor lookups.

    Cache implementations hide whether data came from local persistence or a
    remote EDGIS fetch so higher layers can ask only for system info or
    neighbors.
    """

    def find_system_info(self, system_name: str) -> SystemInfo | None:
        """Return system metadata for the requested name.

        Implementations may satisfy the request from local persistence or fall
        back to a remote fetch and cache-through write on misses.
        """
        ...

    def find_system_neighbors(self, system_info: SystemInfo) -> list[SystemInfo] | None:
        """Return neighbor records for a system payload.

        Implementations may use cached neighbor data when available and fetch
        then persist neighbors only when the cache is empty.
        """
        ...


class ILogger(Protocol):
    """Minimal logging surface used throughout the application.

    The project depends on these Loguru-like methods instead of a concrete
    logger class so tests and alternate logging implementations can be injected
    easily.
    """

    trace: Callable[..., None]
    debug: Callable[..., None]
    info: Callable[..., None]
    warning: Callable[..., None]
    error: Callable[..., None]
    exception: Callable[..., None]
    opt: Callable[..., Any]


class IGis(Protocol):
    """Protocol for remote EDGIS lookups.

    Implementations fetch system metadata by name and neighbor lists by
    coordinate triplet, allowing caches and services to stay independent from
    the concrete HTTP client.
    """

    def fetch_system_info(self, system_name: str) -> SystemInfo | None:
        """Fetch system metadata from the remote EDGIS service.

        Implementations call the upstream API using a system name and return the
        decoded payload or `None` when the lookup fails.
        """
        ...

    def fetch_neighbors(
        self, x: float | int, y: float | int, z: float | int
    ) -> list[SystemInfo] | None:
        """Fetch neighboring systems around a coordinate triplet.

        Implementations call the upstream neighbor endpoint and return the
        decoded neighbor payloads or `None` on failure.
        """
        ...


class IRouteService(Protocol):
    """Top-level application service for route and cache operations.

    Entrypoints depend on this protocol so CLI and Discord surfaces can share
    one high-level API without knowing about the lower-level datasource, cache,
    or algorithm components underneath.
    """

    def init_datasource(
        self, import_dir: str | Path = DEFAULT_INIT_DIR
    ) -> None | Awaitable[None]:
        """Initialize the configured datasource from a directory of seed data.

        Implementations may be synchronous or asynchronous but should perform
        whatever setup and import work the application requires.
        """
        ...

    def get_system_info(self, system_name: str) -> Any | Awaitable[Any]:
        """Return metadata for one system name.

        Implementations resolve the requested system through the application's
        cache and datasource stack and may return either directly or as an
        awaitable result.
        """
        ...

    def get_all_system_names(self) -> Sequence[str] | Awaitable[Sequence[str]]:
        """Return every known system name.

        Implementations expose the application's current system-name set in a
        form suitable for CLI and Discord listing commands.
        """
        ...

    def calc_systems_distance(
        self, system_name_one: str, system_name_two: str
    ) -> float | Awaitable[float]:
        """Return the straight-line distance between two systems.

        Implementations resolve both systems and compute the caller-facing
        distance either synchronously or asynchronously.
        """
        ...

    def path(
        self,
        initial_system_name: str,
        destination_system_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> Sequence[str] | None | Awaitable[Sequence[str] | None]:
        """Calculate a route between two systems.

        Implementations apply the application's route-search algorithm with the
        supplied traversal bounds and progress callback.
        """
        ...

    def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> Sequence[str] | Awaitable[Sequence[str]]:
        """Preload cache entries starting from the supplied seed systems.

        Implementations walk outward from the seeds, cache discovered systems,
        and report progress through the supplied callback.
        """
        ...


class IDiscordContext(Protocol):
    """Protocol for the subset of Discord context behavior the bot uses.

    Command handlers only need to send text responses, so the protocol keeps
    tests lightweight by modeling just that async send capability.
    """

    async def send(self, message: str) -> Any:
        """Send a text response back to Discord.

        Implementations forward the provided message to the active Discord
        channel or context associated with the command invocation.
        """
        ...


class IDiscordBot(Protocol):
    """Protocol for the subset of Discord bot behavior the project needs.

    The wrapper bot composes command registration and runtime startup through
    this narrow surface so tests can substitute lightweight fakes.
    """

    command_prefix: Any
    user: Any
    commands: Any

    def event(self, *args: Any, **kwargs: Any) -> Any:
        """Register an event handler with the bot implementation.

        Implementations return the framework-specific decorator or registration
        result used to bind lifecycle callbacks such as `on_ready`.
        """
        ...

    def command(self, *args: Any, **kwargs: Any) -> Any:
        """Register a command handler with the bot implementation.

        Implementations return the framework-specific decorator or registration
        result used to expose user-invoked commands.
        """
        ...

    def run(self, *args: Any, **kwargs: Any) -> None:
        """Start the bot's runtime loop.

        Implementations connect to Discord and hand control to the underlying
        event loop until shutdown.
        """
        ...


class IBfs(Protocol):
    """Protocol for route-search algorithms based on breadth-first traversal.

    Callers provide start and destination systems plus traversal constraints,
    and implementations return either the discovered path or `None`.
    """

    def travel(
        self,
        start_name: str,
        destination_name: str,
        max_count: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        """Search for a route between two systems.

        Implementations traverse the system graph using the supplied constraints
        and return either the discovered route or `None`.
        """
        ...


class IBulkLoad(Protocol):
    """Protocol for cache preloading algorithms.

    Implementations walk outward from seed systems, load cache data as they go,
    and return the visited systems in caller-visible order.
    """

    def load(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: ProgressFn,
    ) -> list[str]:
        """Preload cache data starting from seed systems.

        Implementations expand outward from the supplied names, cache visited
        systems, and return the order in which systems were loaded.
        """
        ...


class IInitDatasource(Protocol):
    """Protocol for datasource-initialization services.

    The route layer depends on this contract so initialization behavior can be
    provided by a focused service rather than the entrypoint itself.
    """

    def run(self, import_dir: str | Path = DEFAULT_INIT_DIR) -> None:
        """Initialize the datasource from an import directory.

        Implementations coordinate datasource setup and any initial record
        import required by the application.
        """
        ...


class IGetSystemInfo(Protocol):
    """Protocol for services that resolve one system payload by name.

    The abstraction keeps route and distance services independent from the
    specific cache implementation that satisfies system lookups.
    """

    def run(self, system_name: str) -> SystemInfo | None:
        """Resolve one system payload by name.

        Implementations encapsulate the cache or datasource work needed to
        return a system payload or `None` for a miss.
        """
        ...


class IGetAllSystemNames(Protocol):
    """Protocol for services that list all known system names.

    The route layer uses this narrow contract so list-oriented behavior can be
    isolated from datasource details.
    """

    def run(self) -> list[str]:
        """Return all known system names.

        Implementations gather and normalize the application's current system
        names into a simple list for callers.
        """
        ...


class IPathService(Protocol):
    """Protocol for async path-calculation services.

    Implementations adapt route-search algorithms to async callers and return
    either a discovered path or `None`.
    """

    async def run(
        self,
        initial_system_name: str,
        destination_name: str,
        max_systems: int,
        min_distance: int,
        max_distance: int,
        progress_callback: ProgressFn,
    ) -> list[str] | None:
        """Calculate a route for async callers.

        Implementations adapt the route algorithm to async entrypoints and
        return either the discovered path or `None`.
        """
        ...


class ICalcSystemsDistance(Protocol):
    """Protocol for distance-calculation services.

    Implementations resolve two systems and return their straight-line distance
    for callers such as the CLI and Discord command surfaces.
    """

    def run(self, system_name_one: str, system_name_two: str) -> float:
        """Return the straight-line distance between two systems.

        Implementations resolve the systems and compute their Euclidean distance
        for higher-level callers.
        """
        ...


DatasourceProtocol = IDatasource
CacheProtocol = ICache
LoggingProtocol = ILogger
GisProtocol = IGis
RouteServiceProtocol = IRouteService
DiscordContextProtocol = IDiscordContext
DiscordBotProtocol = IDiscordBot
BfsProtocol = IBfs
BulkLoadProtocol = IBulkLoad
InitDatasourceProtocol = IInitDatasource
GetSystemInfoProtocol = IGetSystemInfo
GetAllSystemNamesProtocol = IGetAllSystemNames
PathProtocol = IPathService
CalcSystemsDistanceProtocol = ICalcSystemsDistance

__all__ = [
    "Any",
    "Path",
    "ILogger",
    "SystemInfo",
    "FetchInfoFn",
    "FetchSystemInfoFn",
    "FetchNeighborsFn",
    "DistanceFn",
    "ProgressFn",
    "DatasourceProtocol",
    "CacheProtocol",
    "DiscordBotProtocol",
    "DiscordContextProtocol",
    "LoggingProtocol",
    "GisProtocol",
    "RouteServiceProtocol",
    "BfsProtocol",
    "BulkLoadProtocol",
    "InitDatasourceProtocol",
    "GetSystemInfoProtocol",
    "GetAllSystemNamesProtocol",
    "PathProtocol",
    "CalcSystemsDistanceProtocol",
]
