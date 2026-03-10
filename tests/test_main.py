import sys

import pytest

import main
from tests.helpers import ThreadSafeLogger


class FakeRouteService:
    def __init__(self) -> None:
        self.last_init_import_dir = None
        self.last_bulk_load_args = None
        self.last_distance_args = None
        self.last_system_info_args = None
        self.last_path_args = None

    def get_all_system_names(self):
        return ["Sol", "Lave"]

    def get_system_info(self, name):
        self.last_system_info_args = name
        return {"name": name}

    def calc_systems_distance(self, source, target):
        self.last_distance_args = (source, target)
        return 4.0

    async def path(self, source, target, max_systems=100, min_distance=0, max_distance=10000, progress_callback=None):
        self.last_path_args = (source, target, max_systems, min_distance, max_distance)
        if progress_callback:
            progress_callback("step")
        return [source, target]

    def init_datasource(self, import_dir="./init"):
        self.last_init_import_dir = import_dir

    def bulk_load_cache(self, initial_system_names, max_nodes_visited, progress_callback=None):
        self.last_bulk_load_args = (initial_system_names, max_nodes_visited)
        if progress_callback:
            progress_callback("loaded")
        return initial_system_names


def build_main() -> main.EDMain:
    return main.EDMain.create(logging_utils=ThreadSafeLogger(), route_service=FakeRouteService())  # type: ignore[arg-type]


def test_edmain_validates_constructor_and_create(monkeypatch):  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="logging_utils of type LoggingProtocol is required"):
        main.EDMain(FakeRouteService(), None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="route_service of type RouteServiceProtocol is required"):
        main.EDMain(None, ThreadSafeLogger())  # type: ignore[arg-type]

    monkeypatch.setattr(main, "EDLoggingUtils", lambda: "logger")
    monkeypatch.setattr(main.EDRouteServiceFactory, "create", staticmethod(lambda logging_utils: "route"))
    created = main.EDMain.create()
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


def test_main_commands(monkeypatch, capsys):  # type: ignore[no-untyped-def]
    ed_main = build_main()
    monkeypatch.setattr(main.EDMain, "create", staticmethod(lambda: ed_main))

    # Walk every CLI branch once with a fake route service instead of invoking
    # separate parser/unit tests per command.
    command_sets = [
        ["main.py", "ping"],
        ["main.py", "all_loaded_systems"],
        ["main.py", "system_info", "--system_name", "Sol"],
        ["main.py", "path", "--initial", "Sol", "--destination", "Lave", "--max_systems", "10"],
        ["main.py", "calc_systems_distance", "--initial", "Sol", "--destination", "Lave"],
        ["main.py", "init_datasource", "--import_dir", "./seed"],
        ["main.py", "bulk_load_cache", "--initial_systems", "Sol,Lave", "--max_nodes_visited", "2"],
    ]

    for argv in command_sets:
        monkeypatch.setattr(sys, "argv", argv)
        main.main()

    output = capsys.readouterr().out
    assert "Pong" in output
    assert "All Loaded Systems" in output
    assert "Datasource initialized from ./seed" in output
    assert "Loaded 2 systems from seeds ['Sol', 'Lave']" in output


def test_main_argument_validation_paths(monkeypatch, capsys):  # type: ignore[no-untyped-def]
    ed_main = build_main()
    monkeypatch.setattr(main.EDMain, "create", staticmethod(lambda: ed_main))

    # Each argv set intentionally misses one required argument so we verify the
    # command-level exit paths without depending on stderr formatting.
    invalid_argvs = [
        ["main.py", "system_info"],
        ["main.py", "path", "--destination", "Lave", "--max_systems", "10"],
        ["main.py", "path", "--initial", "Sol", "--max_systems", "10"],
        ["main.py", "path", "--initial", "Sol", "--destination", "Lave", "--max_systems", "1001"],
        ["main.py", "calc_systems_distance", "--destination", "Lave"],
        ["main.py", "calc_systems_distance", "--initial", "Sol"],
        ["main.py", "bulk_load_cache", "--max_nodes_visited", "2"],
        ["main.py", "bulk_load_cache", "--initial_systems", "Sol"],
    ]

    for argv in invalid_argvs:
        monkeypatch.setattr(sys, "argv", argv)
        with pytest.raises(SystemExit):
            main.main()

    assert "Error:" in capsys.readouterr().out
