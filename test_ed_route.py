import ed_route


def main(): ...


def test_small_path():
    assert ed_route.path("Sol", "Sirius") == ["Sol", "Sirius"]


def test_large_path():
    assert ed_route.path("Sol", "Ross 248") == [
        "Sol",
        "Barnard's Star",
        "61 Cygni",
        "Ross 248",
    ]


def test_get_all_system_names():
    assert ed_route.get_all_system_names() != None


if __name__ == "__main__":
    main()
