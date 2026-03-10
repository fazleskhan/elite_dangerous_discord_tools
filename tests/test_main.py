import sys

import main
import pytest


class FakeLoggingUtils:
    def info(self, _message: str, *_args, **_kwargs):
        return None


class FakeRouteService:
    def __init__(self):
        self.last_init_import_dir = None
        self.last_bulk_load_args = None
        self.last_distance_args = None
        self.last_system_info_args = None
        self.last_path_args = None

    def get_all_system_names(self):
        return ["Sol", "Ross 248"]

    def get_system_info(self, name):
        self.last_system_info_args = name
        return {"name": name}

    def calc_systems_distance(self, source, target):
        self.last_distance_args = (source, target)
        return 4.377120022057882

    async def path(
        self,
        source,
        target,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        self.last_path_args = (
            source,
            target,
            max_systems,
            min_distance,
            max_distance,
            progress_callback,
        )
        return [source, "Barnard's Star", "61 Cygni", target]

    def init_datasource(self, import_dir="./init"):
        self.last_init_import_dir = import_dir

    def bulk_load_cache(
        self,
        initial_system_names,
        max_nodes_visited,
        progress_callback=None,
    ):
        self.last_bulk_load_args = (initial_system_names, max_nodes_visited)
        return initial_system_names[:1]


def make_ed_main():
    return main.EDMain.create(
        logging_utils=FakeLoggingUtils(),  # type: ignore[arg-type]
        route_service=FakeRouteService(),  # type: ignore[arg-type]
    )


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        main.EDMain(
            route_service=FakeRouteService(),  # type: ignore[arg-type]
            logging_utils=None,  # type: ignore[arg-type]
        )


def test_get_all_system_names():
    ed_main = make_ed_main()
    assert ed_main.get_all_system_names() == ["Sol", "Ross 248"]


def test_calc_route():
    ed_main = make_ed_main()
    assert ed_main.calc_route("Sol", "Ross 248", 100, 5, 50) == [
        "Sol",
        "Barnard's Star",
        "61 Cygni",
        "Ross 248",
    ]


def test_get_system_info():
    ed_main = make_ed_main()
    system_names = ["Sol", "Barnard's Star", "61 Cygni", "Ross 248"]
    system_infos = ed_main.get_system_info(system_names)
    assert len(system_infos) == 4
    assert system_infos[0] == {"name": "Sol"}


def test_calc_systems_distance():
    ed_main = make_ed_main()
    assert ed_main.calc_systems_distance("Sol", "Alpha Centauri") == 4.377120022057882


def test_init_datasource():
    ed_main = make_ed_main()
    ed_main.init_datasource("./init")
    assert ed_main.route_service.last_init_import_dir == "./init"


def test_main_init_datasource_command(monkeypatch):
    ed_main = make_ed_main()
    monkeypatch.setattr(main.EDMain, "create", lambda: ed_main)
    monkeypatch.setattr(
        sys, "argv", ["main.py", "init_datasource", "--import_dir", "./custom-init"]
    )
    main.main()
    assert ed_main.route_service.last_init_import_dir == "./custom-init"


def test_bulk_load_cache():
    ed_main = make_ed_main()
    assert ed_main.bulk_load_cache(["Sol"], 10) == ["Sol"]
    assert ed_main.route_service.last_bulk_load_args == (["Sol"], 10)


def test_main_bulk_load_cache_command(monkeypatch):
    ed_main = make_ed_main()
    monkeypatch.setattr(main.EDMain, "create", lambda: ed_main)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "main.py",
            "bulk_load_cache",
            "--initial_systems",
            "Sol,Alpha Centauri",
            "--max_nodes_visited",
            "25",
        ],
    )
    main.main()
    assert ed_main.route_service.last_bulk_load_args == (["Sol", "Alpha Centauri"], 25)
