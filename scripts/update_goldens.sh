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

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# === Functions ===

show_help() {
    cat << EOF
${BOLD}Golden Files Update Script${NC}

${BOLD}DESCRIPTION:${NC}
    Updates golden files for language adapter tests. Golden files store expected
    test output for regression testing of code transformations.

${BOLD}USAGE:${NC}
    $0 [LANGUAGE] [OPTIONS]

${BOLD}ARGUMENTS:${NC}
    LANGUAGE        Language adapter to update (python, typescript, etc.)
                    If not specified, updates all languages

${BOLD}OPTIONS:${NC}
    -h, --help      Show this help message
    --list          List available languages and their golden files
    --check         Check which golden files are missing (don't update)
    --dry-run       Show what would be updated without actually updating

${BOLD}ENVIRONMENT VARIABLES:${NC}
    PYTHON_CMD      Python command to use (default: .venv/Scripts/python.exe)
    PYTEST_ARGS     Additional arguments to pass to pytest

${BOLD}EXAMPLES:${NC}
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

${BOLD}NOTES:${NC}
    - Run from project root directory
    - Ensure virtual environment is activated
    - Review changes before committing updated golden files
    - Golden files should be committed to version control

EOF
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're in the project root
check_project_root() {
    if [[ ! -f "pyproject.toml" ]]; then
        log_error "Must be run from project root (directory containing pyproject.toml)"
        exit 1
    fi
}

# Check if Python command is available
check_python() {
    if ! command -v "$PYTHON_CMD" >/dev/null 2>&1; then
        log_error "Python command not found: $PYTHON_CMD"
        log_info "Set PYTHON_CMD environment variable or ensure virtual environment is activated"
        exit 1
    fi
}

# List available languages
list_languages() {
    log_info "Available language adapters:"
    if [[ -d "tests/adapters" ]]; then
        for lang_dir in tests/adapters/*/; do
            if [[ -d "$lang_dir" && ! "$(basename "$lang_dir")" =~ ^(__pycache__|\..*) ]]; then
                lang_name="$(basename "$lang_dir")"
                if [[ "$lang_name" != "__pycache__" && -f "$lang_dir/conftest.py" ]]; then
                    goldens_dir="$lang_dir/goldens"
                    if [[ -d "$goldens_dir" ]]; then
                        golden_count=$(find "$goldens_dir" -name "*.golden" | wc -l)
                        echo -e "  ${GREEN}$lang_name${NC} (${golden_count} golden files)"
                    else
                        echo -e "  ${YELLOW}$lang_name${NC} (no goldens directory)"
                    fi
                fi
            fi
        done
    else
        log_error "tests/adapters directory not found"
        exit 1
    fi
}

# Check missing golden files
check_missing() {
    log_info "Checking for missing golden files..."
    
    local missing_found=false
    
    for lang_dir in tests/adapters/*/; do
        if [[ -d "$lang_dir" && ! "$(basename "$lang_dir")" =~ ^(__pycache__|\..*) ]]; then
            lang_name="$(basename "$lang_dir")"
            if [[ "$lang_name" != "__pycache__" && -f "$lang_dir/conftest.py" ]]; then
                goldens_dir="$lang_dir/goldens"
                
                # Run tests without updating to see which would fail
                log_info "Checking $lang_name..."
                if ! $PYTHON_CMD -m pytest "tests/adapters/$lang_name" -x -q --tb=no >/dev/null 2>&1; then
                    log_warning "Some golden files may be missing for $lang_name"
                    missing_found=true
                else
                    log_success "$lang_name golden files are up to date"
                fi
            fi
        fi
    done
    
    if [[ "$missing_found" == "true" ]]; then
        log_info "Run without --check to update missing golden files"
        exit 1
    else
        log_success "All golden files are present and up to date"
    fi
}

# Update golden files for a specific language
update_language() {
    local language="$1"
    local dry_run="${2:-false}"
    
    local test_path="tests/adapters/$language"
    
    if [[ ! -d "$test_path" ]]; then
        log_error "Language adapter directory not found: $test_path"
        exit 1
    fi
    
    if [[ ! -f "$test_path/conftest.py" ]]; then
        log_error "conftest.py not found in $test_path"
        exit 1
    fi
    
    log_info "Updating golden files for $language..."
    
    if [[ "$dry_run" == "true" ]]; then
        log_info "DRY RUN: Would update golden files for $language"
        log_info "Command: PYTEST_UPDATE_GOLDENS=1 $PYTHON_CMD -m pytest \"$test_path\" $PYTEST_ARGS"
        return 0
    fi
    
    # Create goldens directory if it doesn't exist
    mkdir -p "$test_path/goldens"
    
    # Run tests with golden update flag
    if PYTEST_UPDATE_GOLDENS=1 $PYTHON_CMD -m pytest "$test_path" $PYTEST_ARGS; then
        local golden_count=$(find "$test_path/goldens" -name "*.golden" 2>/dev/null | wc -l)
        log_success "Updated golden files for $language ($golden_count files)"
    else
        log_error "Failed to update golden files for $language"
        exit 1
    fi
}

# Update all languages
update_all() {
    local dry_run="${1:-false}"
    
    log_info "Updating golden files for all languages..."
    
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
        log_error "No language adapters found"
        exit 1
    fi
    
    for language in "${languages[@]}"; do
        update_language "$language" "$dry_run"
    done
    
    if [[ "$dry_run" == "false" ]]; then
        log_success "Updated golden files for all languages: ${languages[*]}"
    fi
}

# === Main Logic ===

main() {
    cd "$PROJECT_ROOT"
    check_project_root
    
    local language=""
    local dry_run=false
    
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
            -*)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
            *)
                if [[ -z "$language" ]]; then
                    language="$1"
                else
                    log_error "Multiple languages specified: $language and $1"
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
        log_info "Golden files updated successfully!"
        log_info "Review the changes and commit the updated golden files:"
        echo -e "  ${BOLD}git add tests/adapters/*/goldens/*.golden${NC}"
        echo -e "  ${BOLD}git commit -m \"Update golden files for language adapters\"${NC}"
    fi
}

# Run main function with all arguments
main "$@"
