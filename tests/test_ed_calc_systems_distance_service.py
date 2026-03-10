import math
import threading

import pytest

import ed_calc_systems_distance_service
from tests.helpers import ThreadSafeLogger


class FakeGetSystemInfoService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def run(self, system_name: str) -> dict[str, object] | None:
        self.calls.append(system_name)
        data = {
            "Sol": {"coords": {"x": 0, "y": 0, "z": 0}},
            "Alpha Centauri": {"coords": {"x": 3, "y": 4, "z": 0}},
        }
        return data.get(system_name)


def test_calc_distance_service_validates_dependencies() -> None:
    with pytest.raises(ValueError, match="logging_utils of type LoggingProtocol is required"):
        ed_calc_systems_distance_service.EDCalcSystemsDistanceService(FakeGetSystemInfoService(), None)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="get_system_info_service of type GetSystemInfoProtocol is required"):
        ed_calc_systems_distance_service.EDCalcSystemsDistanceService(None, ThreadSafeLogger())  # type: ignore[arg-type]


def test_calc_distance_service_calculates_and_caches_coords() -> None:
    logger = ThreadSafeLogger()
    info_service = FakeGetSystemInfoService()
    service = ed_calc_systems_distance_service.EDCalcSystemsDistanceService.create(
        info_service, logger
    )

    assert service.run("Sol", "Alpha Centauri") == pytest.approx(5.0)
    assert service.run("Sol", "Alpha Centauri") == pytest.approx(5.0)
    assert info_service.calls == ["Sol", "Alpha Centauri"]
    assert ("Distance calculated for {} -> {}: {}", ("Sol", "Alpha Centauri", 5.0)) in logger.messages("debug")


def test_calc_distance_service_raises_for_missing_systems() -> None:
    service = ed_calc_systems_distance_service.EDCalcSystemsDistanceService.create(
        FakeGetSystemInfoService(), ThreadSafeLogger()
    )

    with pytest.raises(ValueError, match="Could not load system info for: Missing"):
        service.run("Missing", "Sol")


def test_calc_distance_service_cache_lock_with_threads() -> None:
    info_service = FakeGetSystemInfoService()
    service = ed_calc_systems_distance_service.EDCalcSystemsDistanceService.create(
        info_service, ThreadSafeLogger()
    )
    barrier = threading.Barrier(4)
    results: list[float] = []
    lock = threading.Lock()

    def worker() -> None:
        barrier.wait()
        value = service.run("Sol", "Alpha Centauri")
        with lock:
            results.append(value)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert results == [math.sqrt(25)] * 4
