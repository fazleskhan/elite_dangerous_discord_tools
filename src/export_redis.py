import argparse
import json
from pathlib import Path

import constants
from ed_redis import EDRedis

"""Export cached Redis systems into per-system pretty-printed JSON files."""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export Redis system records into per-system JSON files."
    )
    parser.add_argument(
        "--export-dir",
        default="./data/ed_redis-export",
        help="Output directory for exported JSON files.",
    )
    args = parser.parse_args()

    # Ensure export target exists before writing system files.
    export_dir = Path(args.export_dir)
    export_dir.mkdir(parents=True, exist_ok=True)

    database = EDRedis(database_name="ed_route")
    # Collect system names first, then export each full record individually.
    systems = database.get_all_systems()

    for system in systems:
        system_name = system.get(constants.system_info_name_field)
        if not isinstance(system_name, str) or not system_name:
            continue

        # Fetch each full record by name before writing it out.
        full_system = database.get_system(system_name)
        if full_system is None:
            continue

        output_path = export_dir / f"{_safe_filename(system_name)}.json"
        with output_path.open("w", encoding="utf-8") as file_handle:
            json.dump(
                full_system,
                file_handle,
                indent=2,
                sort_keys=True,
                ensure_ascii=False,
            )
            file_handle.write("\n")


def _safe_filename(system_name: str) -> str:
    # Keep filenames broadly readable while replacing unsafe characters.
    return "".join(
        character if character.isalnum() or character in (" ", "-", "_", ".") else "_"
        for character in system_name
    ).strip()


if __name__ == "__main__":
    main()
