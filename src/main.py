import argparse
import asyncio
import sys
import time
from typing import Any

import ed_factory
from ed_logging_utils import EDLoggingUtils
from ed_constants import default_init_dir
from ed_protocols import LoggingProtocol

"""CLI entrypoint for route search and cache inspection commands."""


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


class EDMain:
    """CLI command compositor exposing route/cache operations."""

    def __init__(
        self, route_service: Any, cache: Any, logging_utils: LoggingProtocol
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils of type LoggingProtocol is required")
        self.route_service = route_service
        self.cache = cache
        self.logging_utils = logging_utils

    @staticmethod
    def create(
        route_service: Any, cache: Any, logging_utils: LoggingProtocol
    ) -> "EDMain":
        return EDMain(route_service, cache, logging_utils)

    def ping(self) -> str:
        return "Pong"

    def get_all_system_names(self) -> list[str]:
        return self.route_service.get_all_system_names()

    def calc_route(
        self,
        source_system: str,
        target_system: str,
        i_max_systems: int,
        min_distance: int = 0,
        max_distance: int = 10000,
    ) -> list[str] | None:
        return asyncio.run(
            self.route_service.path(
                source_system,
                target_system,
                max_systems=i_max_systems,
                min_distance=min_distance,
                max_distance=max_distance,
                progress_callback=lambda message: self.logging_utils.info(message),
            )
        )

    def calc_systems_distance(self, source_system: str, target_system: str) -> float:
        return self.route_service.calc_systems_distance(source_system, target_system)

    def get_system_info(self, system_names: list[str]) -> list[dict[str, Any] | None]:
        return [self.route_service.get_system_info(system_name) for system_name in system_names]

    def init_datasource(self, import_dir: str = default_init_dir) -> None:
        self.route_service.init_datasource(import_dir)

    def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
    ) -> list[str]:
        return self.route_service.bulk_load_cache(
            initial_system_names,
            max_nodes_visited,
            progress_callback=lambda message: self.logging_utils.info(message),
        )


ed_service = ed_factory.create_route_service()
app_logging_utils = EDLoggingUtils()
ed_main = EDMain.create(
    ed_service,
    cache=getattr(ed_service, "cache", None),
    logging_utils=app_logging_utils,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculates pathing and provides information for Elite Dangers GIS data."
    )
    parser.add_argument(
        "command",
        help="enter command (path|system_info|all_loaded_systems|calc_systems_distance|init_datasource|bulk_load_cache)",
        choices=[
            "path",
            "all_loaded_systems",
            "system_info",
            "calc_systems_distance",
            "init_datasource",
            "bulk_load_cache",
            "ping",
        ],
    )
    parser.add_argument("--import_dir", default=default_init_dir)
    parser.add_argument("--initial", nargs="?", const=None, default=None)
    parser.add_argument("--destination", nargs="?", const=None, default=None)
    parser.add_argument("--max_systems", nargs="?", const=None, default=None)
    parser.add_argument("--min_distance", nargs="?", const=None, default=0, type=int)
    parser.add_argument("--max_distance", nargs="?", const=None, default=10000, type=int)
    parser.add_argument("--system_name", nargs="?", const=None, default=None)
    parser.add_argument("--initial_systems", nargs="?", const=None, default=None)
    parser.add_argument("--max_nodes_visited", nargs="?", const=None, default=None, type=int)

    args = parser.parse_args()
    ed_main.logging_utils.info("CLI command received: {}", args.command)

    match args.command:
        case "ping":
            print(ed_main.ping())
        case "all_loaded_systems":
            start = time.perf_counter()
            print("All Loaded Systems: ", get_all_system_names())
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "system_info":
            start = time.perf_counter()
            if not args.system_name:
                print("Error: The --system_name argument is requried with system_info command")
                parser.print_help()
                sys.exit(1)
            print(args.system_name)
            print(get_system_info([args.system_name]))
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "path":
            start = time.perf_counter()
            if not args.initial:
                print("Error: The --initial argument is requried with path command")
                parser.print_help()
                sys.exit(1)
            if not args.destination:
                print("Error: The --destination argument is requried with path command")
                parser.print_help()
                sys.exit(1)
            if args.max_systems and int(args.max_systems) > 1000:
                print("Error: Absolute value --max_systems argument is 1000")
                sys.exit(1)
            route = calc_route(
                args.initial,
                args.destination,
                int(args.max_systems),
                args.min_distance,
                args.max_distance,
            )
            if route:
                print(" → ".join(route))
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "calc_systems_distance":
            start = time.perf_counter()
            if not args.initial:
                print("Error: The --initial argument is requried with calc_systems_distance command")
                parser.print_help()
                sys.exit(1)
            if not args.destination:
                print("Error: The --destination argument is requried with calc_systems_distance command")
                parser.print_help()
                sys.exit(1)
            print(calc_systems_distance(source_system=args.initial, target_system=args.destination))
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "init_datasource":
            start = time.perf_counter()
            init_datasource(args.import_dir)
            print(f"Datasource initialized from {args.import_dir}")
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "bulk_load_cache":
            start = time.perf_counter()
            if not args.initial_systems:
                print("Error: The --initial_systems argument is requried with bulk_load_cache command")
                parser.print_help()
                sys.exit(1)
            if args.max_nodes_visited is None:
                print("Error: The --max_nodes_visited argument is requried with bulk_load_cache command")
                parser.print_help()
                sys.exit(1)
            initial_system_names = [
                system_name.strip()
                for system_name in args.initial_systems.split(",")
                if system_name.strip()
            ]
            loaded_systems = bulk_load_cache(initial_system_names, args.max_nodes_visited)
            print(f"Loaded {len(loaded_systems)} systems from seeds {initial_system_names}")
            print(f"Execution time: {_elapsed_ms(start)} ms")


def get_all_system_names() -> list[str]:
    return ed_main.get_all_system_names()


def calc_route(
    source_system: str,
    target_system: str,
    i_max_systems: int,
    min_distance: int = 0,
    max_distance: int = 10000,
) -> list[str] | None:
    return ed_main.calc_route(
        source_system,
        target_system,
        i_max_systems,
        min_distance,
        max_distance,
    )


def calc_systems_distance(source_system: str, target_system: str) -> float:
    return ed_main.calc_systems_distance(source_system, target_system)


def get_system_info(system_names: list[str]) -> list[dict[str, Any] | None]:
    return ed_main.get_system_info(system_names)


def init_datasource(import_dir: str = default_init_dir) -> None:
    ed_main.init_datasource(import_dir)


def bulk_load_cache(
    initial_system_names: list[str],
    max_nodes_visited: int,
) -> list[str]:
    return ed_main.bulk_load_cache(initial_system_names, max_nodes_visited)


if __name__ == "__main__":
    EDLoggingUtils.create()
    main()
