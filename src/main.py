import ed_route
import constants
import argparse
import sys
from typing import Any

"""CLI entrypoint for route search and cache inspection commands."""


ed_service = ed_route.EDRouteService.create()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Calculates pathing and provides information for Elite Dangers GIS data."
    )
    parser.add_argument(
        "command",
        help="enter command (path|system_info|all_loaded_systems)",
        choices=["path", "all_loaded_systems", "system_info"],
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

    # Dispatch by sub-command and validate required args per command.
    match args.command:
        case "all_loaded_systems":
            print("All Loaded Systems: ", get_all_system_names())
        case "system_info":
            if not args.system_name:
                print(
                    "Error: The --system_name argument is requried with system_info command"
                )
                parser.print_help()
                sys.exit(1)
            print(args.system_name)
            print(get_system_info([args.system_name]))
        case "path":
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
            route = calc_route(args.initial, args.destination, int(args.max_systems))
            if route:
                print(" → ".join(route))


def get_all_system_names() -> list[str]:
    return ed_service.get_all_system_names()


def calc_route(
    source_system: str, target_system: str, i_max_systems: int
) -> list[str] | None:
    return ed_service.path(source_system, target_system, max_systems=i_max_systems)


def get_system_info(system_names: list[str]) -> list[dict[str, Any] | None]:
    results: list[dict[str, Any] | None] = []
    for system_name in system_names:
        results.append(ed_service.get_system_info(system_name))
    return results


if __name__ == "__main__":
    main()
