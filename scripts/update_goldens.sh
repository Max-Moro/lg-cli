#!/bin/bash

# ========================================================================
# Script for updating golden files in language adapter tests
# ========================================================================
# 
# Usage:
#   ./scripts/update_goldens.sh              # Update all golden files
#   ./scripts/update_goldens.sh python       # Update only Python golden files  
#   ./scripts/update_goldens.sh typescript   # Update only TypeScript golden files
#   ./scripts/update_goldens.sh --help       # Show this help
#
# Environment:
#   PYTEST_ARGS     Additional arguments to pass to pytest (optional)
#   PYTHON_CMD      Python command to use (default: .venv/Scripts/python.exe)
#
# Examples:
#   PYTEST_ARGS="-v" ./scripts/update_goldens.sh python
#   PYTHON_CMD="python" ./scripts/update_goldens.sh
#

set -euo pipefail

# === Configuration ===
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEFAULT_PYTHON_CMD=".venv/Scripts/python.exe"

# Use environment variable if set, otherwise use default
PYTHON_CMD="${PYTHON_CMD:-$DEFAULT_PYTHON_CMD}"
PYTEST_ARGS="${PYTEST_ARGS:-}"
VERBOSE=0

# ------------- pretty printing -------------
bold()   { printf '\033[1m%s\033[0m' "$*"; }
green()  { printf '\033[32m%s\033[0m' "$*"; }
yellow() { printf '\033[33m%s\033[0m' "$*"; }
red()    { printf '\033[31m%s\033[0m' "$*"; }

# ------------- logging -------------
log()      { echo "[$(date +%H:%M:%S)] $*"; }
vlog()     { [[ ${VERBOSE:-0} -eq 1 ]] && echo "[$(date +%H:%M:%S)] $*"; }

# === Functions ===

show_help() {
  cat <<EOF
$(bold "update_goldens.sh") — updates golden files for language adapter tests

$(bold "Usage:")
  $(basename "$0") [LANGUAGE] [OPTIONS]

$(bold "Arguments:")
  LANGUAGE        Language adapter to update (python, typescript, etc.)
                  If not specified, updates all languages

$(bold "Options:")
  -h, --help      Show this help message
  --list          List available languages and their golden files
  --check         Check which golden files are missing (don't update)
  --dry-run       Show what would be updated without actually updating
  -v, --verbose   Verbose output

$(bold "Environment Variables:")
  PYTHON_CMD      Python command to use (default: .venv/Scripts/python.exe)
  PYTEST_ARGS     Additional arguments to pass to pytest

$(bold "Examples:")
  # Update all golden files
  $0

  # Update only Python golden files
  $0 python

  # Update with verbose output
  PYTEST_ARGS="-v" $0 typescript

  # List available languages
  $0 --list

  # Check missing golden files
  $0 --check

  # Dry run for Python language
  $0 python --dry-run

$(bold "Notes:")
  - Run from project root directory
  - Ensure virtual environment is activated
  - Review changes before committing updated golden files
  - Golden files should be committed to version control
EOF
}


# Check if we're in the project root
check_project_root() {
    if [[ ! -f "pyproject.toml" ]]; then
        echo "$(red "Error:") Must be run from project root (directory containing pyproject.toml)"
        exit 1
    fi
}

# Check if Python command is available
check_python() {
    if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
        echo "$(red "Error:") Python command not found: $PYTHON_CMD"
        echo "Set PYTHON_CMD environment variable or ensure virtual environment is activated"
        exit 1
    fi
}

# List available languages
list_languages() {
    echo "Available language adapters:"
    if [[ -d "tests/adapters" ]]; then
        for lang_dir in tests/adapters/*/; do
            if [[ -d "$lang_dir" && ! "$(basename "$lang_dir")" =~ ^(__pycache__|\..*) ]]; then
                lang_name="$(basename "$lang_dir")"
                if [[ "$lang_name" != "__pycache__" && -f "$lang_dir/conftest.py" ]]; then
                    goldens_dir="$lang_dir/goldens"
                    if [[ -d "$goldens_dir" ]]; then
                        # Подсчитываем файлы с языковыми расширениями во всех поддиректориях
                        golden_count=0
                        case "$lang_name" in
                            python)
                                golden_count=$(find "$goldens_dir" -name "*.py" | wc -l)
                                ;;
                            typescript)
                                golden_count=$(find "$goldens_dir" -name "*.ts" -o -name "*.tsx" | wc -l)
                                ;;
                            javascript)
                                golden_count=$(find "$goldens_dir" -name "*.js" -o -name "*.jsx" | wc -l)
                                ;;
                            *)
                                # Fallback: ищем файлы с расширением .golden (старый формат)
                                golden_count=$(find "$goldens_dir" -name "*.golden" | wc -l)
                                ;;
                        esac
                        echo "  $(green "$lang_name") (${golden_count} golden files)"
                    else
                        echo "  $(yellow "$lang_name") (no goldens directory)"
                    fi
                fi
            fi
        done
    else
        echo "$(red "Error:") tests/adapters directory not found"
        exit 1
    fi
}

# Check missing golden files
check_missing() {
    echo "Checking for missing golden files..."
    
    local missing_found=false
    
    for lang_dir in tests/adapters/*/; do
        if [[ -d "$lang_dir" && ! "$(basename "$lang_dir")" =~ ^(__pycache__|\..*) ]]; then
            lang_name="$(basename "$lang_dir")"
            if [[ "$lang_name" != "__pycache__" && -f "$lang_dir/conftest.py" ]]; then
                goldens_dir="$lang_dir/goldens"
                
                # Run tests without updating to see which would fail
                echo "• Checking $lang_name..."
                if ! $PYTHON_CMD -m pytest "tests/adapters/$lang_name" -x -q --tb=no >/dev/null 2>&1; then
                    echo "  $(yellow "Warning:") Some golden files may be missing for $lang_name"
                    missing_found=true
                else
                    echo "  $(green "OK") $lang_name golden files are up to date"
                fi
            fi
        fi
    done
    
    if [[ "$missing_found" == "true" ]]; then
        echo "Run without --check to update missing golden files"
        exit 1
    else
        echo "$(green "All golden files are present and up to date")"
    fi
}

# Update golden files for a specific language
update_language() {
    local language="$1"
    local dry_run="${2:-false}"
    
    local test_path="tests/adapters/$language"
    
    if [[ ! -d "$test_path" ]]; then
        echo "$(red "Error:") Language adapter directory not found: $test_path"
        exit 1
    fi
    
    if [[ ! -f "$test_path/conftest.py" ]]; then
        echo "$(red "Error:") conftest.py not found in $test_path"
        exit 1
    fi
    
    echo "$(bold "Language: $language")"
    
    if [[ "$dry_run" == "true" ]]; then
        echo "$(green "Dry-run:") Would update golden files for $language"
        echo "Command: PYTEST_UPDATE_GOLDENS=1 $PYTHON_CMD -m pytest \"$test_path\" $PYTEST_ARGS"
        return 0
    fi
    
    # Create goldens directory if it doesn't exist
    mkdir -p "$test_path/goldens"
    
    # Run tests with golden update flag
    echo "• Updating golden files for $(bold "$language")..."
    if [[ $VERBOSE -eq 1 ]]; then
        set -x
    fi
    
    if PYTEST_UPDATE_GOLDENS=1 $PYTHON_CMD -m pytest "$test_path" $PYTEST_ARGS; then
        # Подсчитываем файлы с языковыми расширениями во всех поддиректориях
        local golden_count=0
        case "$language" in
            python)
                golden_count=$(find "$test_path/goldens" -name "*.py" 2>/dev/null | wc -l)
                ;;
            typescript)
                golden_count=$(find "$test_path/goldens" -name "*.ts" -o -name "*.tsx" 2>/dev/null | wc -l)
                ;;
            javascript)
                golden_count=$(find "$test_path/goldens" -name "*.js" -o -name "*.jsx" 2>/dev/null | wc -l)
                ;;
            *)
                # Fallback: ищем файлы с расширением .golden (старый формат)
                golden_count=$(find "$test_path/goldens" -name "*.golden" 2>/dev/null | wc -l)
                ;;
        esac
        echo "  $(green "OK") Updated golden files for $language ($golden_count files)"
    else
        echo "  $(red "Failed:") Failed to update golden files for $language"
        exit 1
    fi
    
    if [[ $VERBOSE -eq 1 ]]; then
        { set +x; } 2>/dev/null
    fi
}

# Update all languages
update_all() {
    local dry_run="${1:-false}"
    
    echo "$(bold "Updating golden files for all languages")"
    echo
    
    local languages=()
    for lang_dir in tests/adapters/*/; do
        if [[ -d "$lang_dir" && ! "$(basename "$lang_dir")" =~ ^(__pycache__|\..*) ]]; then
            lang_name="$(basename "$lang_dir")"
            if [[ "$lang_name" != "__pycache__" && -f "$lang_dir/conftest.py" ]]; then
                languages+=("$lang_name")
            fi
        fi
    done
    
    if [[ ${#languages[@]} -eq 0 ]]; then
        echo "$(red "Error:") No language adapters found"
        exit 1
    fi
    
    if [[ "$dry_run" == "true" ]]; then
        echo "$(bold "Plan:")"
        for language in "${languages[@]}"; do
            echo "  - $language"
        done
        echo
        echo "$(green "Dry-run") done."
        return 0
    fi
    
    local ok=0
    for language in "${languages[@]}"; do
        update_language "$language" "$dry_run"
        local rc=$?
        if [[ $rc -ne 0 ]]; then
            ok=1
        fi
    done
    
    if [[ $ok -ne 0 ]]; then
        echo
        echo "$(red "One or more language updates failed.")"
        exit 3
    fi
    
    echo
    echo "$(green "All golden files updated successfully for languages:") ${languages[*]}"
}

# === Main Logic ===

main() {
    cd "$PROJECT_ROOT"
    check_project_root
    
    local language=""
    local dry_run=false
    
    if [[ $# -eq 0 ]]; then show_help; exit 1; fi
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            --list)
                list_languages
                exit 0
                ;;
            --check)
                check_python
                check_missing
                exit 0
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=1
                shift
                ;;
            -*)
                echo "$(red "Unknown option") $1"; show_help; exit 1
                ;;
            *)
                if [[ -z "$language" ]]; then
                    language="$1"
                else
                    echo "$(red "Multiple languages specified:") $language and $1"
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    check_python
    
    if [[ -z "$language" ]]; then
        # Update all languages
        update_all "$dry_run"
    else
        # Update specific language
        update_language "$language" "$dry_run"
    fi
    
    if [[ "$dry_run" == "false" ]]; then
        echo
        echo "$(green "Golden files updated successfully!")"
        echo "Review the changes and commit the updated golden files:"
        echo "  $(bold "git add tests/adapters/*/goldens/**/*")"
        echo "  $(bold "git commit -m \"Update golden files for language adapters\"")"
    fi
}

# Run main function with all arguments
main "$@"
