#!/usr/bin/env bash
# =============================================================================
# gen_models.sh — Batch generator for typed models from JSON Schemas
#
# Goals:
#   • Run from ANY module inside the monorepo (CLI, VSCode ext, JetBrains plugins)
#   • Process ALL known schemas in one go (easy to extend)
#   • Support --project switch: cli | vscode | jetbrains
#       - cli       → generate Pydantic v2 models (Python) via datamodel-code-generator
#       - vscode    → (stub) future TS generation (e.g., json-schema-to-typescript)
#       - jetbrains → (stub) future Kotlin generation (e.g., KotlinPoet, KSP)
#
# Location (canonical): <monorepo>/cli/scripts/gen_models.sh
#
# Usage examples:
#   $ ./scripts/gen_models.sh --project cli
#   $ ../cli/scripts/gen_models.sh --project vscode
#
# Options:
#   --project, -p   Project target: cli | vscode | jetbrains (required)
#   --dry-run       Show the plan only, do not execute generators
#   --verbose, -v   Verbose output
#   --help, -h      Show help
#
# Exit codes:
#   0  ok
#   1  usage / bad args
#   2  environment / tool missing
#   3  generation error
# =============================================================================

set -Eeuo pipefail

# ------------- pretty printing -------------
bold()   { printf '\033[1m%s\033[0m' "$*"; }
green()  { printf '\033[32m%s\033[0m' "$*"; }
yellow() { printf '\033[33m%s\033[0m' "$*"; }
red()    { printf '\033[31m%s\033[0m' "$*"; }

# ------------- resolve paths -------------
# Absolute path to this script
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd -P)"
# <monorepo>/cli (parent of scripts)
CLI_DIR="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
# <monorepo> (parent of cli)
MONOREPO_ROOT="$(cd -- "${CLI_DIR}/.." && pwd -P)"

# ------------- defaults / args -------------
PROJECT=""
DRY_RUN=0
VERBOSE=0

usage() {
  cat <<EOF
$(bold "gen_models.sh") — batch generator for typed models from JSON Schemas

$(bold "Usage:")
  $(basename "$0") --project <cli|vscode|jetbrains> [--dry-run] [-v]

$(bold "Examples:")
  (from CLI repo)     ./scripts/gen_models.sh --project cli
  (from VSCode repo)  ../cli/scripts/gen_models.sh --project vscode

$(bold "Options:")
  -p, --project   Target: cli | vscode | jetbrains
      --dry-run   Show the plan; do not run generators
  -v, --verbose   Verbose logs
  -h, --help      Show help
EOF
}

if [[ $# -eq 0 ]]; then usage; exit 1; fi
while [[ $# -gt 0 ]]; do
  case "$1" in
    -p|--project) PROJECT="${2:-}"; shift 2 ;;
    --dry-run)    DRY_RUN=1; shift ;;
    -v|--verbose) VERBOSE=1; shift ;;
    -h|--help)    usage; exit 0 ;;
    *) echo "$(red "Unknown option") $1"; usage; exit 1 ;;
  esac
done

if [[ -z "${PROJECT}" ]]; then
  echo "$(red "Error:") --project is required" >&2
  usage
  exit 1
fi

case "${PROJECT}" in
  cli|vscode|jetbrains) ;;
  *) echo "$(red "Error:") --project must be one of: cli | vscode | jetbrains"; exit 1 ;;
esac

# ------------- helpers -------------
is_windows() {
  case "$(uname -s | tr '[:upper:]' '[:lower:]')" in
    msys*|mingw*|cygwin*) return 0 ;;
    *) return 1 ;;
  esac
}

log()      { echo "[$(date +%H:%M:%S)] $*"; }
vlog()     { [[ $VERBOSE -eq 1 ]] && echo "[$(date +%H:%M:%S)] $*"; }

# Find a Python executable suitable for running `datamodel_code_generator`
find_python() {
  # Priority:
  # 1) active virtualenv
  # 2) <monorepo>/cli/.venv
  # 3) ./.venv under current working dir (fallback)
  # 4) system python (python3, python, py -3)
  local cand=""

  if [[ -n "${VIRTUAL_ENV:-}" ]]; then
    if is_windows; then cand="${VIRTUAL_ENV}/Scripts/python.exe"; else cand="${VIRTUAL_ENV}/bin/python"; fi
    [[ -x "$cand" ]] && echo "$cand" && return 0
  fi

  # prefer CLI venv to keep versions consistent across modules
  if is_windows; then cand="${CLI_DIR}/.venv/Scripts/python.exe"; else cand="${CLI_DIR}/.venv/bin/python"; fi
  [[ -x "$cand" ]] && echo "$cand" && return 0

  if is_windows; then cand="./.venv/Scripts/python.exe"; else cand="./.venv/bin/python"; fi
  [[ -x "$cand" ]] && echo "$cand" && return 0

  if command -v python3 >/dev/null 2>&1; then echo "python3"; return 0; fi
  if command -v python  >/dev/null 2>&1; then echo "python";  return 0; fi
  if command -v py      >/dev/null 2>&1; then echo "py -3";   return 0; fi

  return 1
}

ensure_py_tool() {
  local py="$1"
  # Check `datamodel_code_generator` availability
  if ! "$py" - <<'PY' >/dev/null 2>&1
try:
    import datamodel_code_generator  # noqa: F401
except Exception as e:
    raise SystemExit(1)
PY
  then
    echo "$(red "Error:") Python package $(bold "datamodel-code-generator") is not installed in the selected interpreter:"
    echo "  $(bold "$py")"
    echo "Install it (inside your venv) with:"
    echo "  $py -m pip install 'datamodel-code-generator>=0.25'"
    exit 2
  fi
}

# ------------- discovery (schemas) -------------

# Collect JSON Schema files for CLI project (Python models)
discover_cli_schemas() {
  # Known default location: <monorepo>/cli/lg/*.schema.json
  local dir="${CLI_DIR}/lg"
  local -a found=()
  if [[ -d "$dir" ]]; then
    while IFS= read -r -d '' f; do
      found+=("$f")
    done < <(find "$dir" -maxdepth 1 -type f -name "*.schema.json" -print0)
  fi
  printf '%s\n' "${found[@]:-}"
}

# Map schema path → output target file (Python).
# Default rule: foo.schema.json → foo_schema.py (same directory).
# Override map for special cases (e.g., run_result → api_schema.py).
cli_output_path_for_schema() {
  local schema="$1"
  local base="${schema%".schema.json"}"
  local default_py="${base}_schema.py"

  # Overrides:
  if [[ "$schema" == "${CLI_DIR}/lg/run_result.schema.json" ]]; then
    echo "${CLI_DIR}/lg/api_schema.py"; return 0
  fi

  echo "$default_py"
}

# ------------- generators -------------

generate_cli() {
  local py="$1"

  # Plan
  mapfile -t schemas < <(discover_cli_schemas)
  if [[ ${#schemas[@]} -eq 0 ]]; then
    echo "$(yellow "Warning:") no *.schema.json found in ${CLI_DIR}/lg"
    return 0
  fi

  echo "$(bold "Project: CLI (Python)")"
  echo "Monorepo: ${MONOREPO_ROOT}"
  echo "CLI dir : ${CLI_DIR}"
  echo "Python  : ${py}"
  echo

  # Build plan: list of (schema → output)
  declare -a plan_schema=()
  declare -a plan_output=()
  for s in "${schemas[@]}"; do
    out="$(cli_output_path_for_schema "$s")"
    plan_schema+=("$s")
    plan_output+=("$out")
  done

  echo "$(bold "Plan:")"
  for ((i=0; i<${#plan_schema[@]}; i++)); do
    printf "  - %s\n    → %s\n" "${plan_schema[$i]}" "${plan_output[$i]}"
  done
  echo

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "$(green "Dry-run") done."
    return 0
  fi

  ensure_py_tool "$py"

  # Common generator flags for datamodel-code-generator
  # (keep in sync with existing generated files)
  common_flags=(
    --input-file-type jsonschema
    --target-python-version 3.11
    --use-standard-collections
    --use-schema-description
    --enum-field-as-literal one
    --disable-timestamp
    --output-model-type pydantic_v2.BaseModel
    --base-class pydantic.BaseModel
    --use-field-description
    --strict-nullable
  )

  # Run generation
  local ok=0
  for ((i=0; i<${#plan_schema[@]}; i++)); do
    local in="${plan_schema[$i]}"
    local out="${plan_output[$i]}"
    mkdir -p "$(dirname "$out")"
    echo "• Generating $(bold "$(basename "$out")") from $(basename "$in")"
    if [[ $VERBOSE -eq 1 ]]; then
      set -x
    fi
    # shellcheck disable=SC2086
    $py -m datamodel_code_generator \
      --input "$in" \
      --output "$out" \
      "${common_flags[@]}"
    local rc=$?
    if [[ $VERBOSE -eq 1 ]]; then
      { set +x; } 2>/dev/null
    fi
    if [[ $rc -ne 0 ]]; then
      echo "$(red "Failed:") $in → $out"
      ok=1
    else
      echo "  $(green "OK") $out"
    fi
  done

  if [[ $ok -ne 0 ]]; then
    echo
    echo "$(red "One or more generations failed.")"
    exit 3
  fi

  echo
  echo "$(green "All models generated successfully.")"
}

generate_vscode_stub() {
  echo "$(bold "Project: VS Code Extension (TypeScript)")"
  echo "Monorepo: ${MONOREPO_ROOT}"
  echo
  echo "$(yellow "Note:") TypeScript model generation is not implemented yet."
  echo "Planned toolchain candidates:"
  echo "  - json-schema-to-typescript  (npx json2ts …)"
  echo "  - quicktype                  (npx quicktype …)"
  echo
  echo "When implemented, this mode will:"
  echo "  • discover *.schema.json (shared or CLI schemas)"
  echo "  • emit *.d.ts or .ts models into <monorepo>/vscode/src/models/"
  echo "  • include per-schema override mappings (similar to CLI)"
  [[ $DRY_RUN -eq 1 ]] && echo && echo "$(green "Dry-run") done."
}

generate_jetbrains_stub() {
  echo "$(bold "Project: JetBrains Plugins (Kotlin)")"
  echo "Monorepo: ${MONOREPO_ROOT}"
  echo
  echo "$(yellow "Note:") Kotlin model generation is not implemented yet."
  echo "Planned toolchain candidates:"
  echo "  - custom generator via KotlinPoet"
  echo "  - jsonschema2kotlin or similar (if adopted)"
  echo
  echo "When implemented, this mode will:"
  echo "  • discover *.schema.json (shared or CLI schemas)"
  echo "  • emit Kotlin data classes into <monorepo>/jetbrains-plugin/src/main/kotlin/.../models/"
  echo "  • include per-schema override mappings"
  [[ $DRY_RUN -eq 1 ]] && echo && echo "$(green "Dry-run") done."
}

# ------------- main -------------
case "${PROJECT}" in
  cli)
    PY_EXE="$(find_python || true)"
    if [[ -z "${PY_EXE:-}" ]]; then
      echo "$(red "Error:") Could not locate a Python interpreter. Consider:"
      echo "  • Activating your venv (source .venv/bin/activate) or"
      echo "  • Creating venv in ${CLI_DIR}/.venv and installing dev deps"
      exit 2
    fi
    generate_cli "$PY_EXE"
    ;;
  vscode)
    generate_vscode_stub
    ;;
  jetbrains)
    generate_jetbrains_stub
    ;;
esac
