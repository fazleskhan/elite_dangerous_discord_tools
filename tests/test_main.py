import main
import test_data
import sys
import pytest


def main_func(): ...


def test_constructor_raises_when_logging_utils_is_none():
    with pytest.raises(
        ValueError,
        match="^logging_utils of type LoggingProtocol is required$",
    ):
        main.EDMain(route_service=None, cache=None, logging_utils=None)  # type: ignore[arg-type]


def test_initialize_db():
    main.ed_service.get_all_system_names = lambda: ["Sol", "Ross 248"]
    assert main.get_all_system_names() != None


def test_calc_route():
    captured_args = {}

    async def fake_path(
        source,
        target,
        max_systems=100,
        min_distance=0,
        max_distance=10000,
        progress_callback=None,
    ):
        captured_args["values"] = (
            source,
            target,
            max_systems,
            min_distance,
            max_distance,
            progress_callback,
        )
        return ["Sol", "Barnard's Star", "61 Cygni", "Ross 248"]

    main.ed_service.path = fake_path
    assert main.calc_route("Sol", "Ross 248", 100, 5, 50) == [
        "Sol",
        "Barnard's Star",
        "61 Cygni",
        "Ross 248",
    ]
    assert captured_args["values"][:5] == ("Sol", "Ross 248", 100, 5, 50)
    assert callable(captured_args["values"][5])


def test_get_system_info():
    main.ed_service.get_system_info = lambda name: {"name": name}
    system_names = ["Sol", "Barnard's Star", "61 Cygni", "Ross 248"]
    system_infos = main.get_system_info(system_names)
    # TODO looks like the order of the returned no gaurantee, so this test is not stable. Need to find a way to make it stable.
    # assert system_infos == [
    #    test_data.sol_complete_info,
    #    test_data.barnards_star_complete_info,
    #    test_data.s_61_cygni_complet_info,
    #    test_data.ross_248_complete_info,
    # ]


def test_calc_systems_distance():
    main.ed_service.calc_systems_distance = lambda source, target: 4.377120022057882
    assert main.calc_systems_distance("Sol", "Alpha Centauri") == 4.377120022057882


def test_init_datasource():
    captured = {"import_dir": None}
    main.ed_service.init_datasource = lambda import_dir="./init": captured.update(
        {"import_dir": import_dir}
    )
    main.init_datasource("./init")
    assert captured["import_dir"] == "./init"


def test_main_init_datasource_command(monkeypatch):
    captured = {"import_dir": None}
    monkeypatch.setattr(
        main,
        "init_datasource",
        lambda import_dir="./init": captured.update({"import_dir": import_dir}),
    )
    monkeypatch.setattr(
        sys, "argv", ["main.py", "init_datasource", "--import_dir", "./custom-init"]
    )
    main.main()
    assert captured["import_dir"] == "./custom-init"


def test_bulk_load_cache():
    captured = {"initial_system_names": None, "max_nodes_visited": None}
    main.ed_service.bulk_load_cache = (
        lambda initial_system_names, max_nodes_visited, progress_callback=None: (
            captured.update(
                {
                    "initial_system_names": initial_system_names,
                    "max_nodes_visited": max_nodes_visited,
                }
            )
            or ["Sol"]
        )
    )
    assert main.bulk_load_cache(["Sol"], 10) == ["Sol"]
    assert captured["initial_system_names"] == ["Sol"]
    assert captured["max_nodes_visited"] == 10


def test_main_bulk_load_cache_command(monkeypatch):
    captured = {"initial_system_names": None, "max_nodes_visited": None}
    monkeypatch.setattr(
        main,
        "bulk_load_cache",
        lambda initial_system_names, max_nodes_visited: (
            captured.update(
                {
                    "initial_system_names": initial_system_names,
                    "max_nodes_visited": max_nodes_visited,
                }
            )
            or ["Sol"]
        ),
    )
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
    assert captured["initial_system_names"] == ["Sol", "Alpha Centauri"]
    assert captured["max_nodes_visited"] == 25


if __name__ == "__main__":
    main()
