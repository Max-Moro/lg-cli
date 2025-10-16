#!/usr/bin/env bash
# =============================================================================
# gen_models.sh — Batch generator for typed models from JSON Schemas
#
# Goals:
#   • Run from ANY module inside the monorepo (CLI, VSCode ext, JetBrains plugins)
#   • Process ALL known schemas in one go (easy to extend)
#   • Support --project switch: cli | vscode | jetbrains
#       - cli       → generate Pydantic v2 models (Python) via datamodel-code-generator
#       - vscode    → generate TypeScript models via json-schema-to-typescript (npx json2ts)
#       - jetbrains → generate Kotlin data classes via quicktype (npx, kotlinx.serialization)
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
# <monorepo>/vscode (VS Code extension project)
VSCODE_DIR="${MONOREPO_ROOT}/vscode"
# <monorepo>/intellij (IntelliJ Platform plugin project)
INTELLIJ_DIR="${MONOREPO_ROOT}/intellij"

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

# Try to find a locally installed json2ts (preferred, avoids npx hangs)
find_json2ts_local() {
  local cand=""
  # Prefer VS Code project bin
  if [[ -x "${VSCODE_DIR}/node_modules/.bin/json2ts" ]]; then
    echo "${VSCODE_DIR}/node_modules/.bin/json2ts"; return 0
  fi
  if [[ -x "${VSCODE_DIR}/node_modules/.bin/json2ts.cmd" ]]; then
    echo "${VSCODE_DIR}/node_modules/.bin/json2ts.cmd"; return 0
  fi
  # Fallback: monorepo root (in case tools are hoisted)
  if [[ -x "${MONOREPO_ROOT}/node_modules/.bin/json2ts" ]]; then
    echo "${MONOREPO_ROOT}/node_modules/.bin/json2ts"; return 0
  fi
  if [[ -x "${MONOREPO_ROOT}/node_modules/.bin/json2ts.cmd" ]]; then
    echo "${MONOREPO_ROOT}/node_modules/.bin/json2ts.cmd"; return 0
  fi
  return 1
}

# Node / npx / json2ts availability checks (for VS Code project)
ensure_node_tools() {
  # If local binary/CLI exists — we're good
  if [[ -f "${VSCODE_DIR}/node_modules/json-schema-to-typescript/dist/cli.js" ]] || JSON2TS_BIN="$(find_json2ts_local)"; then
    return 0
  fi

  # Require node and npx
  if ! command -v node >/dev/null 2>&1; then
    echo "$(red "Error:") Node.js is not installed or not in PATH."
    echo "Install Node.js LTS from https://nodejs.org/ and try again."
    exit 2
  fi
  if ! command -v npx >/dev/null 2>&1; then
    echo "$(red "Error:") npx is not available (npm is missing)."
    echo "Install Node.js (with npm) and try again."
    exit 2
  fi
  # Probe that npx can run json2ts (json-schema-to-typescript)
  # Use a very quick version check; allow older npx without --yes.
  if npx --yes json2ts --version >/dev/null 2>&1; then
    return 0
  fi
  if npx json2ts --version >/dev/null 2>&1; then
    return 0
  fi
  # As a final hint
  echo "$(red "Error:") Unable to run $(bold "json2ts") via npx."
  echo "Try: npx --yes json2ts --version"
  exit 2
}

# Node / npx / quicktype availability checks (for JetBrains project)
ensure_quicktype() {
  # Require node and npx
  if ! command -v node >/dev/null 2>&1; then
    echo "$(red "Error:") Node.js is not installed or not in PATH."
    echo "Install Node.js LTS from https://nodejs.org/ and try again."
    exit 2
  fi
  if ! command -v npx >/dev/null 2>&1; then
    echo "$(red "Error:") npx is not available (npm is missing)."
    echo "Install Node.js (with npm) and try again."
    exit 2
  fi
  # Probe that npx can run quicktype
  # Use a very quick version check
  if npx --yes quicktype --version >/dev/null 2>&1; then
    return 0
  fi
  # As a final hint
  echo "$(red "Error:") Unable to run $(bold "quicktype") via npx."
  echo "Try: npx --yes quicktype --version"
  exit 2
}

# ------------- discovery (schemas) -------------

# Collect JSON Schema files for CLI project (Python models)
discover_cli_schemas() {
  # Recursive search in <monorepo>/cli/lg/ and all subdirectories
  local dir="${CLI_DIR}/lg"
  local -a found=()
  if [[ -d "$dir" ]]; then
    while IFS= read -r -d '' f; do
      found+=("$f")
    done < <(find "$dir" -type f -name "*.schema.json" -print0)
  fi
  printf '%s\n' "${found[@]:-}"
}

# Map schema path → output target file (Python).
# Rule: foo.schema.json → foo_schema.py (same directory, preserving subdirectory structure).
cli_output_path_for_schema() {
  local schema="$1"
  local base="${schema%".schema.json"}"
  local default_py="${base}_schema.py"

  echo "$default_py"
}

# Collect JSON Schema files for VS Code project (TypeScript models)
# For now we reuse the same canonical schemas under <monorepo>/cli/lg/*.schema.json
discover_vscode_schemas() {
  discover_cli_schemas
}

# Map schema path → output TypeScript file inside <monorepo>/vscode/src/models/
# Default: foo.schema.json → <vscode>/src/models/foo.ts
vscode_output_path_for_schema() {
  local schema="$1"
  local name="$(basename "${schema}")"
  name="${name%".schema.json"}"
  local out="${VSCODE_DIR}/src/models/${name}.ts"
  # Per-file overrides (if we want custom filenames later)
  # Example:
  # if [[ "$name" == "run_result" ]]; then out="${VSCODE_DIR}/src/models/run_result.ts"; fi
  echo "$out"
}

# Collect JSON Schema files for JetBrains project (Kotlin models)
# Reuse the same canonical schemas under <monorepo>/cli/lg/*.schema.json
discover_jetbrains_schemas() {
  discover_cli_schemas
}

# Map schema path → output Kotlin file inside <monorepo>/intellij/src/main/kotlin/lg/intellij/models/
# Default: foo.schema.json → <intellij>/src/main/kotlin/lg/intellij/models/FooSchema.kt
# Note: Kotlin naming convention uses PascalCase for class names
jetbrains_output_path_for_schema() {
  local schema="$1"
  local name="$(basename "${schema}")"
  name="${name%".schema.json"}"
  
  # Convert snake_case to PascalCase for Kotlin class name
  # Example: diag_report → DiagReport, mode_sets_list → ModeSetsList
  local class_name=""
  IFS='_' read -ra parts <<< "$name"
  for part in "${parts[@]}"; do
    # Capitalize first letter of each part
    class_name+="$(tr '[:lower:]' '[:upper:]' <<< "${part:0:1}")${part:1}"
  done
  class_name+="Schema"  # Add "Schema" suffix
  
  local out="${INTELLIJ_DIR}/src/main/kotlin/lg/intellij/models/${class_name}.kt"
  echo "$out"
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

generate_vscode() {
  echo "$(bold "Project: VS Code Extension (TypeScript)")"
  echo "Monorepo: ${MONOREPO_ROOT}"
  echo "VS Code : ${VSCODE_DIR}"
  echo

  if [[ ! -d "${VSCODE_DIR}/src" ]]; then
    echo "$(red "Error:") VS Code project not found at ${VSCODE_DIR}/src"
    exit 2
  fi

  # Plan
  mapfile -t schemas < <(discover_vscode_schemas)
  if [[ ${#schemas[@]} -eq 0 ]]; then
    echo "$(yellow "Warning:") no *.schema.json found in ${CLI_DIR}/lg"
    return 0
  fi

  echo "$(bold "Plan:")"
  declare -a plan_schema=()
  declare -a plan_output=()
  for s in "${schemas[@]}"; do
    out="$(vscode_output_path_for_schema "$s")"
    plan_schema+=("$s")
    plan_output+=("$out")
  done
  for ((i=0; i<${#plan_schema[@]}; i++)); do
    printf "  - %s\n    → %s\n" "${plan_schema[$i]}" "${plan_output[$i]}"
  done
  echo

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "$(green "Dry-run") done."
    return 0
  fi

  ensure_node_tools

  # -------- Resolve json2ts runner (prefer direct Node CLI over *.cmd shim) --------
  # 1) if local CLI JS exists → run via `node <cli.js>`
  # 2) else if local bin exists → call it directly
  # 3) else fallback to npx
  declare -a JSON2TS
  local CLI_JS="${VSCODE_DIR}/node_modules/json-schema-to-typescript/dist/cli.js"
  if [[ -f "$CLI_JS" ]]; then
    JSON2TS=( node "$CLI_JS" )
  elif JSON2TS_BIN="$(find_json2ts_local)"; then
    JSON2TS=( "$JSON2TS_BIN" )
  else
    JSON2TS=( npx -p json-schema-to-typescript json2ts )
  fi

  # Common options for json2ts
  # Notes:
  #  - We output real .ts modules (not .d.ts) so they are picked by tsconfig include.
  #  - Keep banner small; repos often run formatters/linters afterwards.
  local banner=$'/*\n * AUTO-GENERATED by cli/scripts/gen_models.sh\n * Source: JSON Schemas under cli/lg/*.schema.json\n */'

  local ok=0
  for ((i=0; i<${#plan_schema[@]}; i++)); do
    local in="${plan_schema[$i]}"
    local out="${plan_output[$i]}"
    mkdir -p "$(dirname "$out")"
    echo "• Generating $(bold "$(basename "$out")") from $(basename "$in")"
    if [[ $VERBOSE -eq 1 ]]; then set -x; fi
    # Run either local json2ts or npx-pinned one (array-safe, без eval)
    "${JSON2TS[@]}" \
      -i "$in" \
      -o "$out" \
      --bannerComment "$banner" \
      --cwd "$MONOREPO_ROOT"
    local rc=$?
    if [[ $VERBOSE -eq 1 ]]; then { set +x; } 2>/dev/null; fi
    if [[ $rc -ne 0 ]]; then
      echo "$(red "Failed:") $in → $out"
      ok=1
    else
      echo "  $(green "OK") $out"
    fi
  done

  if [[ $ok -ne 0 ]]; then
    echo
    echo "$(red "One or more TypeScript generations failed.")"
    exit 3
  fi

  echo
  echo "$(green "All TypeScript models generated successfully.")"
}

generate_jetbrains() {
  echo "$(bold "Project: JetBrains Plugin (Kotlin)")"
  echo "Monorepo  : ${MONOREPO_ROOT}"
  echo "IntelliJ  : ${INTELLIJ_DIR}"
  echo
  
  if [[ ! -d "${INTELLIJ_DIR}/src" ]]; then
    echo "$(red "Error:") IntelliJ project not found at ${INTELLIJ_DIR}/src"
    exit 2
  fi
  
  # Plan
  mapfile -t schemas < <(discover_jetbrains_schemas)
  if [[ ${#schemas[@]} -eq 0 ]]; then
    echo "$(yellow "Warning:") no *.schema.json found in ${CLI_DIR}/lg"
    return 0
  fi
  
  echo "$(bold "Plan:")"
  declare -a plan_schema=()
  declare -a plan_output=()
  for s in "${schemas[@]}"; do
    out="$(jetbrains_output_path_for_schema "$s")"
    plan_schema+=("$s")
    plan_output+=("$out")
  done
  for ((i=0; i<${#plan_schema[@]}; i++)); do
    printf "  - %s\n    → %s\n" "${plan_schema[$i]}" "${plan_output[$i]}"
  done
  echo
  
  if [[ $DRY_RUN -eq 1 ]]; then
    echo "$(green "Dry-run") done."
    return 0
  fi
  
  ensure_quicktype
  
  # Common options for quicktype (Kotlin with kotlinx.serialization)
  # Notes:
  #  - --framework kotlinx uses kotlinx.serialization (modern and recommended)
  #  - Package will be lg.intellij.cli.models
  #  - Generates data classes with @Serializable annotations
  local package_name="lg.intellij.cli.models"
  
  local ok=0
  for ((i=0; i<${#plan_schema[@]}; i++)); do
    local in="${plan_schema[$i]}"
    local out="${plan_output[$i]}"
    mkdir -p "$(dirname "$out")"
    echo "• Generating $(bold "$(basename "$out")") from $(basename "$in")"
    if [[ $VERBOSE -eq 1 ]]; then set -x; fi
    
    # Run quicktype via npx
    npx --yes quicktype \
      --lang kotlin \
      --framework kotlinx \
      --src-lang schema \
      --package "$package_name" \
      --out "$out" \
      "$in"
    local rc=$?
    
    if [[ $VERBOSE -eq 1 ]]; then { set +x; } 2>/dev/null; fi
    if [[ $rc -ne 0 ]]; then
      echo "$(red "Failed:") $in → $out"
      ok=1
    else
      echo "  $(green "OK") $out"
    fi
  done
  
  if [[ $ok -ne 0 ]]; then
    echo
    echo "$(red "One or more Kotlin generations failed.")"
    exit 3
  fi
  
  echo
  echo "$(green "All Kotlin models generated successfully.")"
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
    generate_vscode
    ;;
  jetbrains)
    generate_jetbrains
    ;;
esac
