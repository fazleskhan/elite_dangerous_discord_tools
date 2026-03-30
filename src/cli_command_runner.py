import argparse
import time
from typing import TYPE_CHECKING

from protocols import ILogger

if TYPE_CHECKING:
    from main import EDMain


class CLIHandledError(ValueError):
    def __init__(self, message: str, *, show_help: bool = False) -> None:
        super().__init__(message)
        self.show_help = show_help


def elapsed_ms(start: float) -> int:
    return int((time.perf_counter() - start) * 1000)


def raise_usage_error(message: str) -> None:
    raise CLIHandledError(message, show_help=True)


def log_handled_error(
    parser: argparse.ArgumentParser,
    logger: ILogger,
    error: CLIHandledError,
) -> None:
    logger.error("{}", str(error))
    if error.show_help:
        logger.info(parser.format_help())


def log_execution_time(logger: ILogger, start: float) -> None:
    logger.info("Execution time: {} ms", elapsed_ms(start))


def run_command(
    args: argparse.Namespace,
    parser: argparse.ArgumentParser,
    ed_main: "EDMain",
) -> None:
    ed_main.logger.info("CLI command received: {}", args.command)

    match args.command:
        case "ping":
            ed_main.logger.info(ed_main.ping())
        case "all_loaded_systems":
            start = time.perf_counter()
            ed_main.logger.info(
                "All Loaded Systems: {}", ed_main.get_all_system_names()
            )
            log_execution_time(ed_main.logger, start)
        case "system_info":
            start = time.perf_counter()
            if args.system_name is None:
                raise_usage_error(
                    "The --system_name argument is required with system_info command"
                )
            ed_main.logger.info("{}", args.system_name)
            ed_main.logger.info("{}", ed_main.get_system_info([args.system_name]))
            log_execution_time(ed_main.logger, start)
        case "path":
            start = time.perf_counter()
            if args.initial is None:
                raise_usage_error(
                    "The --initial argument is required with path command"
                )
            if args.destination is None:
                raise_usage_error(
                    "The --destination argument is required with path command"
                )
            if args.max_systems is None:
                raise_usage_error(
                    "The --max_systems argument is required with path command"
                )
            max_systems = int(args.max_systems)
            if max_systems > 1000:
                raise_usage_error("Absolute value for --max_systems is 1000")
            route = ed_main.calc_route(
                args.initial,
                args.destination,
                max_systems,
                args.min_distance,
                args.max_distance,
            )
            if route:
                ed_main.logger.info("{}", " -> ".join(route))
            log_execution_time(ed_main.logger, start)
        case "calc_systems_distance":
            start = time.perf_counter()
            if args.initial is None:
                raise_usage_error(
                    "The --initial argument is required with calc_systems_distance command"
                )
            if args.destination is None:
                raise_usage_error(
                    "The --destination argument is required with calc_systems_distance command"
                )
            ed_main.logger.info(
                "{}",
                ed_main.calc_systems_distance(
                    source_system=args.initial,
                    target_system=args.destination,
                ),
            )
            log_execution_time(ed_main.logger, start)
        case "init_datasource":
            start = time.perf_counter()
            ed_main.init_datasource(args.import_dir)
            ed_main.logger.info("Datasource initialized from {}", args.import_dir)
            log_execution_time(ed_main.logger, start)
        case "bulk_load_cache":
            start = time.perf_counter()
            if args.initial_systems is None:
                raise_usage_error(
                    "The --initial_systems argument is required with bulk_load_cache command"
                )
            if args.max_nodes_visited is None:
                raise_usage_error(
                    "The --max_nodes_visited argument is required with bulk_load_cache command"
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
            ed_main.logger.info(
                "Loaded {} systems from seeds {}",
                len(loaded_systems),
                initial_system_names,
            )
            log_execution_time(ed_main.logger, start)
