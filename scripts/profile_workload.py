import argparse
import os
import time

import ed_route


def run_init(import_dir: str, db_path: str) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    service = ed_route.EDRouteService.create(script_file="src/main.py")
    start = time.perf_counter()
    service.init_datasource(import_dir)
    elapsed = time.perf_counter() - start
    print(f"init_elapsed_s={elapsed:.6f}")


def run_path(
    import_dir: str,
    db_path: str,
    initial: str,
    destination: str,
    max_systems: int,
    min_distance: int,
    max_distance: int,
) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    service = ed_route.EDRouteService.create(script_file="src/main.py")
    service.init_datasource(import_dir)

    start = time.perf_counter()
    route = ed_route.asyncio.run(
        service.path(
            initial,
            destination,
            max_systems=max_systems,
            min_distance=min_distance,
            max_distance=max_distance,
            progress_callback=lambda _msg: None,
        )
    )
    elapsed = time.perf_counter() - start
    hops = 0 if not route else len(route)
    print(f"path_elapsed_s={elapsed:.6f}")
    print(f"path_hops={hops}")


def run_distance_loop(
    import_dir: str,
    db_path: str,
    initial: str,
    destination: str,
    iterations: int,
) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    service = ed_route.EDRouteService.create(script_file="src/main.py")
    service.init_datasource(import_dir)

    start = time.perf_counter()
    distance = 0.0
    for _ in range(iterations):
        distance = service.calc_systems_distance(initial, destination)
    elapsed = time.perf_counter() - start
    print(f"distance_elapsed_s={elapsed:.6f}")
    print(f"distance_value={distance:.12f}")
    print(f"distance_iterations={iterations}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["init", "path", "distance_loop"])
    parser.add_argument("--import_dir", default="./init")
    parser.add_argument("--db", default="/tmp/ed_profile.db")
    parser.add_argument("--initial", default="Sol")
    parser.add_argument("--destination", default="Ross 248")
    parser.add_argument("--max_systems", type=int, default=1000)
    parser.add_argument("--min_distance", type=int, default=0)
    parser.add_argument("--max_distance", type=int, default=10000)
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()

    os.environ["DB_LOCATION"] = args.db

    if args.mode == "init":
        run_init(args.import_dir, args.db)
    elif args.mode == "path":
        run_path(
            args.import_dir,
            args.db,
            args.initial,
            args.destination,
            args.max_systems,
            args.min_distance,
            args.max_distance,
        )
    else:
        run_distance_loop(
            args.import_dir,
            args.db,
            args.initial,
            args.destination,
            args.iterations,
        )


if __name__ == "__main__":
    main()
