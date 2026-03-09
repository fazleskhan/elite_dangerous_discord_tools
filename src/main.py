import ed_factory
import constants
import argparse
import asyncio
import sys
import time
from typing import Any
from loguru import logger
from logging_utils import setup_logging

"""CLI entrypoint for route search and cache inspection commands."""

ed_service = ed_factory.create_route_service()


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


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
        ],
    )
    parser.add_argument(
        "--import_dir",
        default="./init",
        # Only used by the `init_datasource` command.
        help="directory containing datasource JSON files for init_datasource command",
    )
    parser.add_argument(
        "--initial",
        nargs="?",
        const=None,
        default=None,
        help="the initial system to path from (for example Sol) required if comand is path",
    )
    parser.add_argument(
        "--destination",
        nargs="?",
        const=None,
        default=None,
        help="the final system to path to (for example Terravor) required if comand is path",
    )
    parser.add_argument(
        "--max_systems",
        nargs="?",
        const=None,
        default=None,
        help="over how many systems the search will operate. Beware setting this value to high will dramatically increase runtime. Abolute maximum of 1000",
    )
    parser.add_argument(
        "--min_distance",
        nargs="?",
        const=None,
        default=0,
        type=int,
        help="minimum edge distance allowed for path traversal",
    )
    parser.add_argument(
        "--max_distance",
        nargs="?",
        const=None,
        default=10000,
        type=int,
        help="maximum edge distance allowed for path traversal",
    )
    parser.add_argument(
        "--system_name",
        nargs="?",
        const=None,
        default=None,
        help="the system name to return info for (for example Beta Hydri) required if comand is system_info",
    )
    parser.add_argument(
        "--initial_systems",
        nargs="?",
        const=None,
        default=None,
        help="comma-separated seed systems required for bulk_load_cache (for example Sol,Alpha Centauri)",
    )
    parser.add_argument(
        "--max_nodes_visited",
        nargs="?",
        const=None,
        default=None,
        type=int,
        help="maximum number of systems to visit required for bulk_load_cache",
    )

    args = parser.parse_args()
    logger.info("CLI command received: {}", args.command)

    # Dispatch by sub-command and validate required args per command.
    match args.command:
        case "all_loaded_systems":
            start = time.perf_counter()
            logger.debug("Listing all loaded systems")
            print("All Loaded Systems: ", get_all_system_names())
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "system_info":
            start = time.perf_counter()
            if not args.system_name:
                logger.error("Missing required --system_name for system_info command")
                print(
                    "Error: The --system_name argument is requried with system_info command"
                )
                parser.print_help()
                sys.exit(1)
            logger.debug("Fetching system info for {}", args.system_name)
            print(args.system_name)
            print(get_system_info([args.system_name]))
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "path":
            start = time.perf_counter()
            if not args.initial:
                logger.error("Missing required --initial for path command")
                print("Error: The --initial argument is requried with path command")
                parser.print_help()
                sys.exit(1)
            if not args.destination:
                logger.error("Missing required --destination for path command")
                print("Error: The --destination argument is requried with path command")
                parser.print_help()
                sys.exit(1)
            if args.max_systems and int(args.max_systems) > 1000:
                logger.error("Invalid --max_systems value: {}", args.max_systems)
                print("Error: Absolute value --max_systems argument is 1000")
                sys.exit(1)
            logger.info(
                "Calculating path source={} destination={} max_systems={} min_distance={} max_distance={}",
                args.initial,
                args.destination,
                args.max_systems,
                args.min_distance,
                args.max_distance,
            )
            route = calc_route(
                args.initial,
                args.destination,
                int(args.max_systems),
                args.min_distance,
                args.max_distance,
            )
            if route:
                logger.info("Route found with hop_count={}", len(route))
                print(" → ".join(route))
            else:
                logger.warning("No route found")
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "calc_systems_distance":
            start = time.perf_counter()
            if not args.initial:
                logger.error(
                    "Missing required --initial for calc_systems_distance command"
                )
                print(
                    "Error: The --initial argument is requried with calc_systems_distance command"
                )
                parser.print_help()
                sys.exit(1)
            if not args.destination:
                logger.error(
                    "Missing required --destination for calc_systems_distance command"
                )
                print(
                    "Error: The --destination argument is requried with calc_systems_distance command"
                )
                parser.print_help()
                sys.exit(1)
            logger.info(
                "Calculating distance source={} destination={}",
                args.initial,
                args.destination,
            )
            print(
                calc_systems_distance(
                    source_system=args.initial, target_system=args.destination
                )
            )
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "init_datasource":
            start = time.perf_counter()
            init_datasource(args.import_dir)
            print(f"Datasource initialized from {args.import_dir}")
            print(f"Execution time: {_elapsed_ms(start)} ms")
        case "bulk_load_cache":
            start = time.perf_counter()
            if not args.initial_systems:
                logger.error("Missing required --initial_systems for bulk_load_cache")
                print(
                    "Error: The --initial_systems argument is requried with bulk_load_cache command"
                )
                parser.print_help()
                sys.exit(1)
            if args.max_nodes_visited is None:
                logger.error("Missing required --max_nodes_visited for bulk_load_cache")
                print(
                    "Error: The --max_nodes_visited argument is requried with bulk_load_cache command"
                )
                parser.print_help()
                sys.exit(1)
            initial_system_names = [
                system_name.strip()
                for system_name in args.initial_systems.split(",")
                if system_name.strip()
            ]
            loaded_systems = bulk_load_cache(
                initial_system_names,
                args.max_nodes_visited,
            )
            print(
                f"Loaded {len(loaded_systems)} systems from seeds {initial_system_names}"
            )
            print(f"Execution time: {_elapsed_ms(start)} ms")


def get_all_system_names() -> list[str]:
    return ed_service.get_all_system_names()


def calc_route(
    source_system: str,
    target_system: str,
    i_max_systems: int,
    min_distance: int = 0,
    max_distance: int = 10000,
) -> list[str] | None:
    return asyncio.run(
        ed_service.path(
            source_system,
            target_system,
            max_systems=i_max_systems,
            min_distance=min_distance,
            max_distance=max_distance,
            progress_callback=lambda message: logger.info(message),
        )
    )


def calc_systems_distance(source_system: str, target_system: str) -> float:
    return ed_service.calc_systems_distance(source_system, target_system)


def get_system_info(system_names: list[str]) -> list[dict[str, Any] | None]:
    return [ed_service.get_system_info(system_name) for system_name in system_names]


def init_datasource(import_dir: str = "./init") -> None:
    ed_service.init_datasource(import_dir)


def bulk_load_cache(
    initial_system_names: list[str], max_nodes_visited: int
) -> list[str]:
    return ed_service.bulk_load_cache(
        initial_system_names,
        max_nodes_visited,
        progress_callback=lambda message: logger.info(message),
    )


if __name__ == "__main__":
    setup_logging()
    main()
