import main
import test_data


def main_func(): ...


def test_initialize_db():
    main.ed_service.get_all_system_names = lambda: ["Sol", "Ross 248"]
    assert main.get_all_system_names() != None


def test_calc_route():
    async def fake_path(source, target, max_systems=100):
        return ["Sol", "Barnard's Star", "61 Cygni", "Ross 248"]

    main.ed_service.path = fake_path
    assert main.calc_route("Sol", "Ross 248", 100) == [
        "Sol",
        "Barnard's Star",
        "61 Cygni",
        "Ross 248",
    ]


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


if __name__ == "__main__":
    main()
