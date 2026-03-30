import sys
from typing import Any

import pytest

import main
from tests.helpers import ThreadSafeLogger


class FakeRouteService:
    def __init__(self) -> None:
        self.last_init_import_dir: str | None = None
        self.last_bulk_load_args: tuple[list[str], int] | None = None
        self.last_distance_args: tuple[str, str] | None = None
        self.last_system_info_args: str | None = None
        self.last_path_args: tuple[str, str, int, int, int] | None = None

    def get_all_system_names(self) -> list[str]:
        return ["Sol", "Lave"]

    def get_system_info(self, name: str) -> dict[str, str]:
        self.last_system_info_args = name
        return {"name": name}

    def calc_systems_distance(self, source: str, target: str) -> float:
        self.last_distance_args = (source, target)
        return 4.0

    async def path(
        self,
        source: str,
        target: str,
        max_systems: int = 100,
        min_distance: int = 0,
        max_distance: int = 10000,
        progress_callback: Any = None,
    ) -> list[str]:
        self.last_path_args = (source, target, max_systems, min_distance, max_distance)
        if progress_callback:
            progress_callback("step")
        return [source, target]

    def init_datasource(self, import_dir: str = "./init") -> None:
        self.last_init_import_dir = import_dir

    def bulk_load_cache(
        self,
        initial_system_names: list[str],
        max_nodes_visited: int,
        progress_callback: Any = None,
    ) -> list[str]:
        self.last_bulk_load_args = (initial_system_names, max_nodes_visited)
        if progress_callback:
            progress_callback("loaded")
        return initial_system_names


def build_main() -> main.EDMain:
    return main.EDMain.create(
        logging_utils=ThreadSafeLogger(),
        route_service=FakeRouteService(),
    )


def test_edmain_validates_constructor_and_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="logging_utils must not be null"):
        main.EDMain(FakeRouteService(), None)
    with pytest.raises(ValueError, match="route_service must not be null"):
        main.EDMain(None, ThreadSafeLogger())

    monkeypatch.setattr(
        main.EDRouteServiceFactory,
        "create",
        staticmethod(lambda logging_utils: "route"),
    )
    created = main.EDMain.create(logging_utils="logger")
    assert created.logging_utils == "logger"
    assert created.route_service == "route"


def test_edmain_methods_delegate() -> None:
    ed_main = build_main()
    assert ed_main.ping() == "Pong"
    assert ed_main.get_all_system_names() == ["Sol", "Lave"]
    assert ed_main.calc_route("Sol", "Lave", 10, 1, 20) == ["Sol", "Lave"]
    assert ed_main.calc_systems_distance("Sol", "Lave") == 4.0
    assert ed_main.get_system_info(["Sol"]) == [{"name": "Sol"}]
    ed_main.init_datasource("./seed")
    assert ed_main.route_service.last_init_import_dir == "./seed"
    assert ed_main.bulk_load_cache(["Sol"], 3) == ["Sol"]


def test_elapsed_ms_returns_int() -> None:
    assert isinstance(main._elapsed_ms(0.0), int)


def test_main_commands(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ed_main = build_main()
    logger = ed_main.logging_utils
    assert isinstance(logger, ThreadSafeLogger)
    configure_calls = 0
    create_args: list[ThreadSafeLogger] = []

    monkeypatch.setattr(main, "configure_logging", lambda: _configured())
    monkeypatch.setattr(main, "logger", logger)

    def _configured() -> None:
        nonlocal configure_calls
        configure_calls += 1

    def fake_create(
        logging_utils: ThreadSafeLogger | None = None,
        route_service: FakeRouteService | None = None,
    ) -> main.EDMain:
        assert route_service is None
        assert logging_utils is logger
        assert logging_utils is not None
        create_args.append(logging_utils)
        return ed_main

    monkeypatch.setattr(main.EDMain, "create", staticmethod(fake_create))

    command_sets = [
        ["main.py", "ping"],
        ["main.py", "all_loaded_systems"],
        ["main.py", "system_info", "--system_name", "Sol"],
        [
            "main.py",
            "path",
            "--initial",
            "Sol",
            "--destination",
            "Lave",
            "--max_systems",
            "10",
        ],
        [
            "main.py",
            "calc_systems_distance",
            "--initial",
            "Sol",
            "--destination",
            "Lave",
        ],
        ["main.py", "init_datasource", "--import_dir", "./seed"],
        [
            "main.py",
            "bulk_load_cache",
            "--initial_systems",
            "Sol,Lave",
            "--max_nodes_visited",
            "2",
        ],
    ]

    for argv in command_sets:
        monkeypatch.setattr(sys, "argv", argv)
        main.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    assert configure_calls == len(command_sets)
    assert len(create_args) == len(command_sets)
    assert ("info", "Pong", ()) in logger.calls
    assert ("info", "All Loaded Systems: {}", (["Sol", "Lave"],)) in logger.calls
    assert ("info", "Datasource initialized from {}", ("./seed",)) in logger.calls
    assert (
        "info",
        "Loaded {} systems from seeds {}",
        (2, ["Sol", "Lave"]),
    ) in logger.calls
    assert any(
        level == "info" and message == "CLI parameters: {}"
        for level, message, _args in logger.calls
    )


def test_main_argument_validation_paths(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    ed_main = build_main()
    logger = ed_main.logging_utils
    assert isinstance(logger, ThreadSafeLogger)
    monkeypatch.setattr(main, "configure_logging", lambda: None)
    monkeypatch.setattr(main, "logger", logger)
    monkeypatch.setattr(
        main.EDMain, "create", staticmethod(lambda logging_utils=None: ed_main)
    )

    invalid_argvs = [
        ["main.py", "system_info"],
        ["main.py", "path", "--destination", "Lave", "--max_systems", "10"],
        ["main.py", "path", "--initial", "Sol", "--max_systems", "10"],
        [
            "main.py",
            "path",
            "--initial",
            "Sol",
            "--destination",
            "Lave",
            "--max_systems",
            "1001",
        ],
        ["main.py", "calc_systems_distance", "--destination", "Lave"],
        ["main.py", "calc_systems_distance", "--initial", "Sol"],
        ["main.py", "bulk_load_cache", "--max_nodes_visited", "2"],
        ["main.py", "bulk_load_cache", "--initial_systems", "Sol"],
    ]

    for argv in invalid_argvs:
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit):
            main.main()

    captured = capsys.readouterr()
    assert captured.out == ""
    error_calls = [
        (message, args) for level, message, args in logger.calls if level == "error"
    ]
    assert len(error_calls) == len(invalid_argvs)
    assert any("required" in str(args[0]) for _message, args in error_calls)
    assert any(
        level == "info" and message.startswith("usage:")
        for level, message, _args in logger.calls
    )


def test_log_handled_error_logs_message_and_help() -> None:
    logger = ThreadSafeLogger()
    parser = main._build_parser()

    main._log_handled_error(
        parser,
        logger,
        main.CLIHandledError("bad input", show_help=True),
    )

    assert ("error", "{}", ("bad input",)) in logger.calls
    assert any(
        level == "info" and message.startswith("usage:")
        for level, message, _args in logger.calls
    )
