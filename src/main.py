import argparse
import asyncio
import time
from pathlib import Path
from typing import Any

from defaults import DEFAULT_INIT_DIR
from constants import default_init_dir
from app_logging import EDLoggingUtils
from ed_route import EDRouteService
from ed_route_service_factory import EDRouteServiceFactory
from protocols import ILogger

"""CLI entrypoint for route search and cache inspection commands."""


def _elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


class EDMain:
    """CLI command compositor exposing route/cache operations."""

    def __init__(
        self,
        route_service: EDRouteService | None,
        logging_utils: ILogger | None,
    ) -> None:
        if logging_utils is None:
            raise ValueError("logging_utils must not be null")
        if route_service is None:
            raise ValueError("route_service must not be null")
        self.route_service = route_service
        self.logging_utils = logging_utils

    @staticmethod
    def create(
        logging_utils: ILogger | None = None,
        route_service: EDRouteService | None = None,
    ) -> "EDMain":
        resolved_logging_utils = logging_utils or EDLoggingUtils.create()
        resolved_route_service = route_service

        if resolved_route_service is None:
            resolved_route_service = EDRouteServiceFactory.create(
                logging_utils=resolved_logging_utils,
            )

        return EDMain(
            route_service=resolved_route_service,
            logging_utils=resolved_logging_utils,
        )

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
        return [
            self.route_service.get_system_info(system_name)
            for system_name in system_names
        ]

    def init_datasource(self, import_dir: str | Path = DEFAULT_INIT_DIR) -> None:
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


def _build_parser() -> argparse.ArgumentParser:
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
    parser.add_argument(
        "--max_distance", nargs="?", const=None, default=10000, type=int
    )
    parser.add_argument("--system_name", nargs="?", const=None, default=None)
    parser.add_argument("--initial_systems", nargs="?", const=None, default=None)
    parser.add_argument(
        "--max_nodes_visited", nargs="?", const=None, default=None, type=int
    )
    return parser


def _log_help_and_exit(
    parser: argparse.ArgumentParser,
    logging_utils: ILogger,
    message: str,
) -> None:
    logging_utils.error(message)
    logging_utils.info(parser.format_help())
    raise SystemExit(1)


def _log_execution_time(logging_utils: ILogger, start: float) -> None:
    logging_utils.info("Execution time: {} ms", _elapsed_ms(start))


def _run_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    ed_main: EDMain,
) -> None:
    ed_main.logging_utils.info("CLI command received: {}", args.command)

    match args.command:
        case "ping":
            ed_main.logging_utils.info(ed_main.ping())
        case "all_loaded_systems":
            start = time.perf_counter()
            ed_main.logging_utils.info(
                "All Loaded Systems: {}", ed_main.get_all_system_names()
            )
            _log_execution_time(ed_main.logging_utils, start)
        case "system_info":
            start = time.perf_counter()
            if args.system_name is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --system_name argument is required with system_info command",
                )
            ed_main.logging_utils.info("{}", args.system_name)
            ed_main.logging_utils.info(
                "{}", ed_main.get_system_info([args.system_name])
            )
            _log_execution_time(ed_main.logging_utils, start)
        case "path":
            start = time.perf_counter()
            if args.initial is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --initial argument is required with path command",
                )
            if args.destination is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --destination argument is required with path command",
                )
            if args.max_systems is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --max_systems argument is required with path command",
                )
            max_systems = int(args.max_systems)
            if max_systems > 1000:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "Absolute value for --max_systems is 1000",
                )
            route = ed_main.calc_route(
                args.initial,
                args.destination,
                max_systems,
                args.min_distance,
                args.max_distance,
            )
            if route:
                ed_main.logging_utils.info("{}", " -> ".join(route))
            _log_execution_time(ed_main.logging_utils, start)
        case "calc_systems_distance":
            start = time.perf_counter()
            if args.initial is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --initial argument is required with calc_systems_distance command",
                )
            if args.destination is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --destination argument is required with calc_systems_distance command",
                )
            ed_main.logging_utils.info(
                "{}",
                ed_main.calc_systems_distance(
                    source_system=args.initial,
                    target_system=args.destination,
                ),
            )
            _log_execution_time(ed_main.logging_utils, start)
        case "init_datasource":
            start = time.perf_counter()
            ed_main.init_datasource(args.import_dir)
            ed_main.logging_utils.info(
                "Datasource initialized from {}", args.import_dir
            )
            _log_execution_time(ed_main.logging_utils, start)
        case "bulk_load_cache":
            start = time.perf_counter()
            if args.initial_systems is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --initial_systems argument is required with bulk_load_cache command",
                )
            if args.max_nodes_visited is None:
                _log_help_and_exit(
                    parser,
                    ed_main.logging_utils,
                    "The --max_nodes_visited argument is required with bulk_load_cache command",
                )
            initial_system_names = [
                system_name.strip()
                for system_name in args.initial_systems.split(",")
                if system_name.strip()
            ]
            loaded_systems = ed_main.bulk_load_cache(
                initial_system_names,
                args.max_nodes_visited,
            )
            ed_main.logging_utils.info(
                "Loaded {} systems from seeds {}",
                len(loaded_systems),
                initial_system_names,
            )
            _log_execution_time(ed_main.logging_utils, start)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    ed_main = EDMain.create()
    _run_command(args, parser, ed_main)


if __name__ == "__main__":
    main()
