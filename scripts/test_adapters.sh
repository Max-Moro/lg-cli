#!/usr/bin/env bash
# Test runner for language adapters with flexible filtering
# Allows running tests for specific optimizations and languages
#
# Usage:
#   ./scripts/test_adapters.sh [OPTIMIZATIONS] [LANGUAGES] [UPDATE_GOLDENS]
#
# Arguments:
#   OPTIMIZATIONS  - Comma-separated list of optimization types or 'all'
#   LANGUAGES      - Comma-separated list of languages or 'all'
#   UPDATE_GOLDENS - 'true' to regenerate golden files, 'false' otherwise (default: false)
#
# Examples:
#   ./scripts/test_adapters.sh all python                          # All tests for Python
#   ./scripts/test_adapters.sh comments python,typescript          # Specific optimization for multiple languages
#   ./scripts/test_adapters.sh function_bodies,public_api all      # Multiple optimizations for all languages
#   ./scripts/test_adapters.sh imports python true                 # Update golden files for imports in Python
#   ./scripts/test_adapters.sh all all                             # Run everything
#
# Note: 'literals' category includes all literal-related tests:
#   - test_literals.py
#   - test_literal_comment_context.py
#   - test_literal_sets.py
#   - test_literals_indentation.py
#
# The script automatically scans available languages and optimization types from the test directory structure.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ADAPTERS_DIR="$PROJECT_ROOT/tests/adapters"

# Color output helpers
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_error() {
    echo -e "${RED}ERROR: $1${NC}" >&2
}

print_success() {
    echo -e "${GREEN}$1${NC}"
}

print_info() {
    echo -e "${BLUE}$1${NC}"
}

print_warning() {
    echo -e "${YELLOW}$1${NC}"
}

# Scan available languages
scan_languages() {
    local languages=()
    for dir in "$ADAPTERS_DIR"/*; do
        if [[ -d "$dir" ]]; then
            local lang_name=$(basename "$dir")
            # Skip special directories
            if [[ ! "$lang_name" =~ ^[._] ]] && [[ "$lang_name" != "golden_utils.py" ]] && [[ "$lang_name" != "golden_utils.md" ]]; then
                languages+=("$lang_name")
            fi
        fi
    done
    echo "${languages[@]}"
}

# Scan available optimization types for a language
scan_optimizations() {
    local lang=$1
    local optimizations=()
    local has_literals=false

    if [[ ! -d "$ADAPTERS_DIR/$lang" ]]; then
        return
    fi

    for test_file in "$ADAPTERS_DIR/$lang"/test_*.py; do
        if [[ -f "$test_file" ]]; then
            local opt_name=$(basename "$test_file" .py)
            opt_name=${opt_name#test_}

            # Group all literal* tests under single "literals" category
            if [[ "$opt_name" == literal* ]]; then
                if [[ "$has_literals" == false ]]; then
                    optimizations+=("literals")
                    has_literals=true
                fi
            else
                optimizations+=("$opt_name")
            fi
        fi
    done

    echo "${optimizations[@]}"
}

# Get all unique optimization types across all languages
scan_all_optimizations() {
    local all_opts=()
    local languages=($(scan_languages))
    local has_literals=false

    for lang in "${languages[@]}"; do
        # Scan test files directly to properly group literals
        if [[ ! -d "$ADAPTERS_DIR/$lang" ]]; then
            continue
        fi

        for test_file in "$ADAPTERS_DIR/$lang"/test_*.py; do
            if [[ -f "$test_file" ]]; then
                local opt_name=$(basename "$test_file" .py)
                opt_name=${opt_name#test_}

                # Group all literal* tests under single "literals" category
                if [[ "$opt_name" == literal* ]]; then
                    if [[ "$has_literals" == false ]]; then
                        all_opts+=("literals")
                        has_literals=true
                    fi
                else
                    # Add to array if not already present
                    if [[ ! " ${all_opts[@]} " =~ " ${opt_name} " ]]; then
                        all_opts+=("$opt_name")
                    fi
                fi
            fi
        done
    done

    # Sort alphabetically
    IFS=$'\n' sorted=($(sort <<<"${all_opts[*]}"))
    echo "${sorted[@]}"
}

# Print usage and available options
print_usage() {
    local languages=($(scan_languages))
    local optimizations=($(scan_all_optimizations))

    cat <<EOF
Usage: $0 [OPTIMIZATIONS] [LANGUAGES] [UPDATE_GOLDENS]

Arguments:
  OPTIMIZATIONS  Which optimization types to test (comma-separated or 'all')
  LANGUAGES      Which languages to test (comma-separated or 'all')
  UPDATE_GOLDENS Whether to regenerate golden files ('true'/'false', default: 'false')

Available languages:
  ${languages[@]}

Available optimization types:
  ${optimizations[@]}

Examples:
  # Run all tests for Python
  $0 all python

  # Run comments tests for Python and TypeScript
  $0 comments python,typescript

  # Run function_bodies and public_api tests for all languages
  $0 function_bodies,public_api all

  # Update golden files for imports tests in Python
  $0 imports python true

  # Run all tests for all languages
  $0 all all

  # Show this help
  $0

Note:
  'literals' category includes all literal-related tests (literals, literal_comment_context,
  literal_sets, literals_indentation). Not all languages have all subtypes.
EOF
}

# Validate optimization names
validate_optimizations() {
    local requested_opts=$1
    local all_opts=($(scan_all_optimizations))

    if [[ "$requested_opts" == "all" ]]; then
        echo "${all_opts[@]}"
        return 0
    fi

    IFS=',' read -ra opts <<< "$requested_opts"
    local validated=()

    for opt in "${opts[@]}"; do
        opt=$(echo "$opt" | xargs) # trim whitespace
        if [[ " ${all_opts[@]} " =~ " ${opt} " ]]; then
            validated+=("$opt")
        else
            print_warning "Unknown optimization type: $opt (skipping)"
        fi
    done

    if [[ ${#validated[@]} -eq 0 ]]; then
        print_error "No valid optimization types specified"
        return 1
    fi

    echo "${validated[@]}"
}

# Validate language names
validate_languages() {
    local requested_langs=$1
    local all_langs=($(scan_languages))

    if [[ "$requested_langs" == "all" ]]; then
        echo "${all_langs[@]}"
        return 0
    fi

    IFS=',' read -ra langs <<< "$requested_langs"
    local validated=()

    for lang in "${langs[@]}"; do
        lang=$(echo "$lang" | xargs) # trim whitespace
        if [[ " ${all_langs[@]} " =~ " ${lang} " ]]; then
            validated+=("$lang")
        else
            print_warning "Unknown language: $lang (skipping)"
        fi
    done

    if [[ ${#validated[@]} -eq 0 ]]; then
        print_error "No valid languages specified"
        return 1
    fi

    echo "${validated[@]}"
}

# Build pytest path patterns for given optimizations and language
build_test_paths() {
    local lang=$1
    shift
    local optimizations=("$@")

    local paths=()

    for opt in "${optimizations[@]}"; do
        # Special handling for "literals" category - include all literal* tests
        if [[ "$opt" == "literals" ]]; then
            for test_file in "$ADAPTERS_DIR/$lang"/test_literal*.py; do
                if [[ -f "$test_file" ]]; then
                    paths+=("$test_file")
                fi
            done
        else
            local test_file="$ADAPTERS_DIR/$lang/test_${opt}.py"
            if [[ -f "$test_file" ]]; then
                paths+=("$test_file")
            fi
        fi
    done

    echo "${paths[@]}"
}

# Main execution
main() {
    # Parse arguments
    local optimizations_arg="${1:-}"
    local languages_arg="${2:-}"
    local update_goldens="${3:-false}"

    # Show help if no arguments
    if [[ -z "$optimizations_arg" ]] || [[ -z "$languages_arg" ]]; then
        print_usage
        exit 0
    fi

    # Validate and expand arguments
    local optimizations=($(validate_optimizations "$optimizations_arg")) || exit 1
    local languages=($(validate_languages "$languages_arg")) || exit 1

    # Print summary
    print_info "=== Test Adapter Configuration ==="
    print_info "Optimizations: ${optimizations[*]}"
    print_info "Languages: ${languages[*]}"
    print_info "Update goldens: $update_goldens"
    echo ""

    # Set up environment for golden updates if requested
    local env_prefix=""
    if [[ "$update_goldens" == "true" ]] || [[ "$update_goldens" == "1" ]]; then
        env_prefix="PYTEST_UPDATE_GOLDENS=1"
        print_warning "Golden files will be UPDATED"
        echo ""
    fi

    # Collect all test paths
    local all_test_paths=()

    for lang in "${languages[@]}"; do
        local lang_paths=($(build_test_paths "$lang" "${optimizations[@]}"))

        if [[ ${#lang_paths[@]} -eq 0 ]]; then
            print_warning "No matching tests found for language: $lang"
            continue
        fi

        all_test_paths+=("${lang_paths[@]}")
    done

    if [[ ${#all_test_paths[@]} -eq 0 ]]; then
        print_error "No test files found matching the specified criteria"
        exit 1
    fi

    # Print test files to be run
    print_info "=== Test files to run ==="
    for path in "${all_test_paths[@]}"; do
        echo "  - $(realpath --relative-to="$PROJECT_ROOT" "$path")"
    done
    echo ""

    # Run pytest with compact output
    cd "$PROJECT_ROOT"

    if [[ -n "$env_prefix" ]]; then
        eval "$env_prefix python -m pytest ${all_test_paths[*]} -q --tb=no -r fE --disable-warnings"
    else
        python -m pytest "${all_test_paths[@]}" -q --tb=no -r fE --disable-warnings
    fi

    exit $?
}

main "$@"
