import argparse

from ed_constants import default_init_dir


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calculates pathing and provides information for Elite Dangers GIS data."
    )
    parser.add_argument(
        "command",
        help="enter command (path|system_info|all_loaded_systems|calc_systems_distance|init_datasource|bulk_load_cache)",
        choices=[
            "path",
            "all_loaded_systems",
            "system_info",
            "calc_systems_distance",
            "init_datasource",
            "bulk_load_cache",
            "ping",
        ],
    )
    parser.add_argument("--import_dir", default=default_init_dir)
    parser.add_argument("--initial", nargs="?", const=None, default=None)
    parser.add_argument("--destination", nargs="?", const=None, default=None)
    parser.add_argument("--max_systems", nargs="?", const=None, default=None)
    parser.add_argument("--min_distance", nargs="?", const=None, default=0, type=int)
    parser.add_argument(
        "--max_distance", nargs="?", const=None, default=10000, type=int
    )
    parser.add_argument("--system_name", nargs="?", const=None, default=None)
    parser.add_argument("--initial_systems", nargs="?", const=None, default=None)
    parser.add_argument(
        "--max_nodes_visited", nargs="?", const=None, default=None, type=int
    )
    return parser
