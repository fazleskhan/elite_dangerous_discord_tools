import ed_route
import constants
import argparse
import logging
import asyncio
import sys
from typing import Any
from logging_utils import resolve_log_level

"""CLI entrypoint for route search and cache inspection commands."""

logger = logging.getLogger(__name__)


ed_service = ed_route.EDRouteService.create()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculates pathing and provides information for Elite Dangers GIS data."
    )
    parser.add_argument(
        "command",
        help="enter command (path|system_info|all_loaded_systems|calc_systems_distance)",
        choices=["path", "all_loaded_systems", "system_info", "calc_systems_distance"],
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
        "--system_name",
        nargs="?",
        const=None,
        default=None,
        help="the system name to return info for (for example Beta Hydri) required if comand is system_info",
    )

    args = parser.parse_args()
    logger.info("CLI command received: %s", args.command)

    # Dispatch by sub-command and validate required args per command.
    match args.command:
        case "all_loaded_systems":
            logger.debug("Listing all loaded systems")
            print("All Loaded Systems: ", get_all_system_names())
        case "system_info":
            if not args.system_name:
                logger.error("Missing required --system_name for system_info command")
                print(
                    "Error: The --system_name argument is requried with system_info command"
                )
                parser.print_help()
                sys.exit(1)
            logger.debug("Fetching system info for %s", args.system_name)
            print(args.system_name)
            print(get_system_info([args.system_name]))
        case "path":
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
                logger.error("Invalid --max_systems value: %s", args.max_systems)
                print("Error: Absolute value --max_systems argument is 1000")
                sys.exit(1)
            logger.info(
                "Calculating path source=%s destination=%s max_systems=%s",
                args.initial,
                args.destination,
                args.max_systems,
            )
            route = calc_route(args.initial, args.destination, int(args.max_systems))
            if route:
                logger.info("Route found with hop_count=%s", len(route))
                print(" → ".join(route))
            else:
                logger.warning("No route found")
        case "calc_systems_distance":
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
                "Calculating distance source=%s destination=%s",
                args.initial,
                args.destination,
            )
            print(
                calc_systems_distance(
                    source_system=args.initial, target_system=args.destination
                )
            )


def get_all_system_names() -> list[str]:
    return ed_service.get_all_system_names()


def calc_route(
    source_system: str, target_system: str, i_max_systems: int
) -> list[str] | None:
    return asyncio.run(
        ed_service.path(source_system, target_system, max_systems=i_max_systems)
    )


def calc_systems_distance(source_system: str, target_system: str) -> float:
    return ed_service.calc_systems_distance(source_system, target_system)


def get_system_info(system_names: list[str]) -> list[dict[str, Any] | None]:
    results: list[dict[str, Any] | None] = []
    for system_name in system_names:
        results.append(ed_service.get_system_info(system_name))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=resolve_log_level(logging.INFO))
    main()
