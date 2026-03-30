"""CLI entrypoint and command surface.

[README:CLI_ENTRYPOINT]
### CLI Entrypoint
Entrypoint: `python src/main.py <command> [options]`

Overview: Unified synchronous CLI for route search, system inspection,
cache inspection, distance checks, datasource initialization, and bulk cache
loading.

Commands and available arguments:

* `ping`
  * Overview: Health check command that returns `Pong`.
  * Arguments: none.
* `all_loaded_systems`
  * Overview: Lists all currently cached/loaded system names.
  * Arguments: none.
* `system_info`
  * Overview: Fetches and prints system info payload for a single system.
  * Arguments: `--system_name` (required).
* `path`
  * Overview: Computes a route between source and destination using BFS-based
    traversal and distance bounds.
  * Arguments: `--initial` (required), `--destination` (required),
    `--max_systems` (required, max `1000`), `--min_distance` (optional,
    default `0`), `--max_distance` (optional, default `10000`).
* `calc_systems_distance`
  * Overview: Computes Euclidean distance between two systems.
  * Arguments: `--initial` (required), `--destination` (required).
* `init_datasource`
  * Overview: Imports seed JSON records into the configured datasource.
  * Arguments: `--import_dir` (optional, default `default_init_dir`).
* `bulk_load_cache`
  * Overview: Performs breadth-first cache preloading from seed systems.
  * Arguments: `--initial_systems` (required, comma-separated seeds),
    `--max_nodes_visited` (required).
[/README]

[README:STARTING]
Run the CLI entrypoint via:

`python ./src/main.py <command> [options]`
[/README]
"""

import asyncio
from pathlib import Path
from typing import Any

try:
    from autologging import traced
except ImportError:

    def traced(target: Any) -> Any:
        return target


from app_logging import configure_logging
from cli_command_runner import (
    CLIHandledError,
    elapsed_ms,
    log_handled_error as _log_handled_error,
    run_command as _run_command,
)
from cli_parser import build_cli_parser as _build_parser
from defaults import DEFAULT_INIT_DIR
from ed_route import EDRouteService
from ed_route_service_factory import EDRouteServiceFactory
from loguru import logger
from protocols import ILogger

_elapsed_ms = elapsed_ms


@traced
class EDMain:
    """CLI command compositor exposing route/cache operations."""

    def __init__(
        self,
        route_service: EDRouteService | None,
        logger: ILogger | None,
    ) -> None:
        if logger is None:
            raise ValueError("logger must not be null")
        if route_service is None:
            raise ValueError("route_service must not be null")
        self.route_service = route_service
        self.logger = logger

    @staticmethod
    def create(
        logger: ILogger | None = None,
        route_service: EDRouteService | None = None,
    ) -> "EDMain":
        if logger is None:
            raise ValueError("logger must not be null")
        resolved_route_service = route_service

        if resolved_route_service is None:
            resolved_route_service = EDRouteServiceFactory.create(
                logger=logger,
            )

        return EDMain(
            route_service=resolved_route_service,
            logger=logger,
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
                progress_callback=self.logger.info,
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
            progress_callback=self.logger.info,
        )


def main() -> None:
    parser = _build_parser()
    configure_logging()
    app_logger = logger
    args = parser.parse_args()
    app_logger.info("CLI parameters: {}", vars(args))
    ed_main = EDMain.create(logger=app_logger)
    try:
        _run_command(args, parser, ed_main)
    except CLIHandledError as error:
        _log_handled_error(parser, app_logger, error)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
