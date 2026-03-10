import ed_route
from ed_route_service_factory import EDRouteServiceFactory
import pytest
import test_data


def main(): ...


class FakeLoggingUtils:
    def debug(self, _message: str, *_args, **_kwargs):
        return None

    def info(self, _message: str, *_args, **_kwargs):
        return None

    def warning(self, _message: str, *_args, **_kwargs):
        return None

    def error(self, _message: str, *_args, **_kwargs):
        return None


class FakeDB:
    def init_datasource(self, import_dir: str = "./init"):
        return None

    def get_all_systems(self):
        return [{"name": "Sol"}, {"name": "Sirius"}]


class FakeCache:
    def find_system_info(self, system_name: str):
        return {"name": system_name}

    def find_system_neighbors(self, system_info):
        return []


class FakeBfs:
    def travel(
        self,
        source,
        destination,
        max_systems,
        min_distance,
        max_distance,
        progress_callback,
    ):
        if source == "Sol" and destination == "Sirius":
            return ["Sol", "Sirius"]
        if source == "Sol" and destination == "Ross 248":
            return ["Sol", "Barnard's Star", "61 Cygni", "Ross 248"]
        return None


def make_service():
    return EDRouteServiceFactory.create(
        logging_utils=FakeLoggingUtils(),
        datasource=FakeDB(),
        cache=FakeCache(),
        bfs=FakeBfs(),
    )


@pytest.mark.asyncio
async def test_small_path():
    ed_service = make_service()
    assert await ed_service.path(
        "Sol", "Sirius", 100, 0, 10000, lambda _message: None
    ) == ["Sol", "Sirius"]


@pytest.mark.asyncio
async def test_large_path():
    ed_service = make_service()
    assert await ed_service.path(
        "Sol", "Ross 248", 100, 0, 10000, lambda _message: None
    ) == [
        "Sol",
        "Barnard's Star",
        "61 Cygni",
        "Ross 248",
    ]


def test_get_all_system_names():
    ed_service = make_service()
    assert ed_service.get_all_system_names() != None


def test_get_system_info():
    ed_service = make_service()
    assert ed_service.get_system_info("Sol") != None


def test_calc_systems_distance():
    ed_service = make_service()
    systems = {
        "Sol": test_data.sol_data,
        "Alpha Centauri": test_data.alpha_centauri_data,
    }
    ed_service._calc_systems_distance_service._get_system_info_service.run = (
        lambda name: systems.get(name)
    )

    distance = ed_service.calc_systems_distance("Sol", "Alpha Centauri")
    assert distance == pytest.approx(4.377120022057882)


if __name__ == "__main__":
    main()
