import ed_route


def main(): ...


def test_small_path():
    ed_service = ed_route.EDRouteService.create()
    assert ed_service.path("Sol", "Sirius") == ["Sol", "Sirius"]


def test_large_path():
    ed_service = ed_route.EDRouteService.create()
    assert ed_service.path("Sol", "Ross 248") == [
        "Sol",
        "Barnard's Star",
        "61 Cygni",
        "Ross 248",
    ]


def test_get_all_system_names():
    ed_service = ed_route.EDRouteService.create()
    assert ed_service.get_all_system_names() != None


def test_get_system_info():
    ed_service = ed_route.EDRouteService.create()
    assert ed_service.get_system_info("Sol") != None


if __name__ == "__main__":
    main()
