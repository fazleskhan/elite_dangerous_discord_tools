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

import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_PATH = ROOT / "docs" / "README_TEMPLATE.md"
README_PATH = ROOT / "README.md"

PLACEHOLDER_RE = re.compile(r"\{\{README:(?P<key>[A-Z0-9_]+)\}\}")
START_RE = re.compile(r"^\[README:(?P<key>[A-Z0-9_]+)\]$")
END_RE = re.compile(r"^\[/README\]$")

README_CLASS_DOC_ORDER: list[tuple[str, str]] = [
    ("main.py", "EDMain"),
    ("ed_discord_bot.py", "EDDiscordBot"),
    ("ed_route.py", "EDRouteService"),
    ("ed_route_service_factory.py", "EDRouteServiceFactory"),
    ("ed_app_logging.py", "InterceptHandler"),
    ("ed_app_logging.py", "_LoguruConfigWatcher"),
    ("ed_redis.py", "EDRedis"),
    ("ed_tinydb.py", "EDTinyDB"),
    ("ed_edgis.py", "EDGis"),
    ("ed_edgis_cache.py", "EDGisCache"),
    ("ed_bfs_algo.py", "EDBfsAlgo"),
    ("ed_bulk_load_algo.py", "EDBulkLoadAlgo"),
]


def _docstring_summary(docstring: str | None) -> str:
    if not docstring:
        return ""
    paragraphs = [
        part.strip() for part in docstring.strip().split("\n\n") if part.strip()
    ]
    if not paragraphs:
        return ""
    return " ".join(line.strip() for line in paragraphs[0].splitlines())


def _load_module_ast(source_path: Path) -> ast.Module:
    return ast.parse(source_path.read_text(encoding="utf-8"))


def _public_method_nodes(
    class_node: ast.ClassDef,
) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    methods: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for node in class_node.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name.startswith("_") and node.name != "__init__":
            continue
        methods.append(node)
    return methods


def _render_class_doc_section(source_path: Path, class_name: str) -> str:
    module = _load_module_ast(source_path)
    class_node = next(
        (
            node
            for node in module.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if class_node is None:
        raise ValueError(f"Missing class {class_name} in {source_path}")

    class_summary = _docstring_summary(ast.get_docstring(class_node))
    if not class_summary:
        raise ValueError(f"Missing docstring summary for {class_name} in {source_path}")

    lines = [
        f"### `{class_name}`",
        "",
        f"Source: `src/{source_path.name}`",
        "",
        class_summary,
    ]

    method_lines: list[str] = []
    for method_node in _public_method_nodes(class_node):
        method_summary = _docstring_summary(ast.get_docstring(method_node))
        if not method_summary:
            raise ValueError(
                f"Missing docstring summary for {class_name}.{method_node.name} in {source_path}"
            )
        method_lines.append(f"* `{method_node.name}`: {method_summary}")

    if method_lines:
        lines.extend(["", "Key methods:", *method_lines])

    return "\n".join(lines)


def _collect_docstring_sections() -> dict[str, str]:
    rendered_sections = [
        _render_class_doc_section(ROOT / "src" / filename, class_name)
        for filename, class_name in README_CLASS_DOC_ORDER
    ]
    return {"CODE_OVERVIEW": "\n\n".join(rendered_sections)}


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

    sections = {
        key: "\n\n".join(body for body in bodies if body)
        for key, bodies in collected.items()
    }
    sections.update(_collect_docstring_sections())
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
