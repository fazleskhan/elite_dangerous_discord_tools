#!/usr/bin/env bash
#
# [README:SCRIPTS]
# ### `generate_plantuml_local.sh`
#
# Regenerates PlantUML diagram PNGs locally from the repository's `.puml` sources
# under `docs/diagrams` using the local Java and `plantuml.jar` installation.
#
# Usage:
# - `bash scripts/generate_plantuml_local.sh`
# - `bash scripts/generate_plantuml_local.sh docs/diagrams/class_structure.puml`
#
# Arguments:
# - Optional `.puml` file paths under `docs/diagrams`. When omitted, the script
#   regenerates every diagram PNG in the repository.
#
# Environment variables:
# - `JAVA_BIN`: Path to the Java executable used to run PlantUML.
# - `PLANTUML_JAR`: Path to the local `plantuml.jar` file.
#
# [/README]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIAGRAM_DIR="${REPO_ROOT}/docs/diagrams"

JAVA_BIN="${JAVA_BIN:-/usr/bin/java}"
PLANTUML_JAR="${PLANTUML_JAR:-/usr/share/plantuml/plantuml.jar}"

usage() {
  cat <<'USAGE'
Generate PlantUML PNGs locally (no PlantUML server).

Usage:
  scripts/generate_plantuml_local.sh
  scripts/generate_plantuml_local.sh docs/diagrams/foo/bar.puml [more .puml files...]

Behavior:
  - No arguments: generates PNGs for all .puml files in docs/diagrams.
  - With arguments: generates PNGs only for the provided .puml files.
  - Output PNG is written next to each source .puml file.

Environment variables:
  JAVA_BIN      Path to java binary (default: /usr/bin/java)
  PLANTUML_JAR  Path to plantuml.jar (default: /usr/share/plantuml/plantuml.jar)
USAGE
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ ! -x "${JAVA_BIN}" ]]; then
  echo "Error: Java binary not found or not executable: ${JAVA_BIN}" >&2
  exit 1
fi

if [[ ! -f "${PLANTUML_JAR}" ]]; then
  echo "Error: PlantUML jar not found: ${PLANTUML_JAR}" >&2
  exit 1
fi

if [[ ! -d "${DIAGRAM_DIR}" ]]; then
  echo "Error: diagrams directory not found: ${DIAGRAM_DIR}" >&2
  exit 1
fi

declare -a targets=()

if [[ "$#" -eq 0 ]]; then
  while IFS= read -r -d '' file; do
    targets+=("${file}")
  done < <(find "${DIAGRAM_DIR}" -type f -name '*.puml' -print0 | sort -z)
else
  for input in "$@"; do
    if [[ ! -f "${input}" ]]; then
      echo "Error: file not found: ${input}" >&2
      exit 1
    fi

    if [[ "${input}" != *.puml ]]; then
      echo "Error: not a .puml file: ${input}" >&2
      exit 1
    fi

    resolved_input="$(realpath "${input}")"
    case "${resolved_input}" in
      "${DIAGRAM_DIR}"/*) ;;
      *)
        echo "Error: file must be inside ${DIAGRAM_DIR}: ${input}" >&2
        exit 1
        ;;
    esac

    targets+=("${resolved_input}")
  done
fi

if [[ "${#targets[@]}" -eq 0 ]]; then
  echo "No .puml files found in ${DIAGRAM_DIR}" >&2
  exit 1
fi

echo "Generating ${#targets[@]} diagram(s) with local PlantUML..."
# cspell:disable-next-line
"${JAVA_BIN}" -Djava.awt.headless=true -jar "${PLANTUML_JAR}" -tpng "${targets[@]}"
echo "Done."
