#!/usr/bin/env python3
"""Generate README.md from docs/README_TEMPLATE.md and source docstring sections."""

from __future__ import annotations

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "docs" / "README_TEMPLATE.md"
README_PATH = ROOT / "README.md"

SECTION_RE = re.compile(
    r"\[README:(?P<key>[A-Z0-9_]+)\]\n(?P<body>.*?)\n\[/README\]",
    re.DOTALL,
)
PLACEHOLDER_RE = re.compile(r"\{\{README:(?P<key>[A-Z0-9_]+)\}\}")


def _extract_docstring_sections(source_path: Path) -> dict[str, str]:
    module = ast.parse(source_path.read_text(encoding="utf-8"))
    docstring = ast.get_docstring(module)
    if docstring is None:
        return {}

    sections: dict[str, str] = {}
    for match in SECTION_RE.finditer(docstring):
        key = match.group("key")
        body = match.group("body").strip()
        sections[key] = body
    return sections


def _collect_sections() -> dict[str, str]:
    sections: dict[str, str] = {}
    for source_path in sorted((ROOT / "src").glob("*.py")):
        extracted = _extract_docstring_sections(source_path)
        for key, body in extracted.items():
            if key in sections:
                raise ValueError(
                    f"Duplicate README section key '{key}' found in {source_path}"
                )
            sections[key] = body
    return sections


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
