#!/usr/bin/env python3
"""
[README:SCRIPTS]
### `generate_readme.py`

Assembles `README.md` from `docs/README_TEMPLATE.md` plus embedded `[README:...]` blocks
stored in repository source files and scripts.

Usage:
- `python scripts/generate_readme.py`

Arguments:
- This script takes no command-line arguments.

[/README]
Generate README.md from docs/README_TEMPLATE.md and embedded source documentation sections.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "docs" / "README_TEMPLATE.md"
README_PATH = ROOT / "README.md"

PLACEHOLDER_RE = re.compile(r"\{\{README:(?P<key>[A-Z0-9_]+)\}\}")
START_RE = re.compile(r"^\[README:(?P<key>[A-Z0-9_]+)\]$")
END_RE = re.compile(r"^\[/README\]$")


def _normalize_readme_line(line: str) -> str:
    stripped = line.rstrip("\n")
    if stripped.startswith("# "):
        return stripped[2:]
    if stripped == "#":
        return ""
    return stripped


def _extract_sections(source_path: Path) -> dict[str, list[str]]:
    lines = source_path.read_text(encoding="utf-8").splitlines()
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    current_body: list[str] = []

    for raw_line in lines:
        normalized = _normalize_readme_line(raw_line).strip()
        start_match = START_RE.match(normalized)
        if start_match:
            if current_key is not None:
                raise ValueError(f"Nested README section in {source_path}")
            current_key = start_match.group("key")
            current_body = []
            continue

        if current_key is not None and END_RE.match(normalized):
            body = "\n".join(current_body).strip()
            sections.setdefault(current_key, []).append(body)
            current_key = None
            current_body = []
            continue

        if current_key is not None:
            current_body.append(_normalize_readme_line(raw_line))

    if current_key is not None:
        raise ValueError(
            f"Unterminated README section '{current_key}' in {source_path}"
        )

    return sections


def _collect_sections_from_glob(pattern: str) -> dict[str, list[str]]:
    sections: dict[str, list[str]] = {}
    for source_path in sorted(ROOT.glob(pattern)):
        extracted = _extract_sections(source_path)
        for key, bodies in extracted.items():
            sections.setdefault(key, []).extend(bodies)
    return sections


def _collect_sections() -> dict[str, str]:
    collected: dict[str, list[str]] = {}

    for source_sections in (
        _collect_sections_from_glob("src/*.py"),
        _collect_sections_from_glob("scripts/*.py"),
        _collect_sections_from_glob("scripts/*.sh"),
    ):
        for key, bodies in source_sections.items():
            collected.setdefault(key, []).extend(bodies)

    return {
        key: "\n\n".join(body for body in bodies if body)
        for key, bodies in collected.items()
    }


def _render_template(template: str, sections: dict[str, str]) -> str:
    missing_keys: set[str] = set()

    def replace(match: re.Match[str]) -> str:
        key = match.group("key")
        if key not in sections:
            missing_keys.add(key)
            return ""
        return sections[key]

    rendered = PLACEHOLDER_RE.sub(replace, template)
    if missing_keys:
        missing = ", ".join(sorted(missing_keys))
        raise ValueError(f"Missing README docstring sections: {missing}")

    return rendered.rstrip() + "\n"


def main() -> None:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    sections = _collect_sections()
    readme = _render_template(template, sections)
    README_PATH.write_text(readme, encoding="utf-8")


if __name__ == "__main__":
    main()
