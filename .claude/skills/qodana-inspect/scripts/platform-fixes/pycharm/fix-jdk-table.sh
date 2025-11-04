#!/bin/bash

# PyCharm/Python Platform Fix: jdk.table.xml Generator
# Fixes QD-11375: Python SDK not synced with jdk.table.xml in native mode
# This script generates jdk.table.xml from project .idea/misc.xml when Qodana fails to create it

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_FILE="$SCRIPT_DIR/jdk.table.tpl.xml"

# Colors for output
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[PyCharm Fix]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[PyCharm Fix]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[PyCharm Fix]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[PyCharm Fix]${NC} $1" >&2
}

# Find Qodana config directory
find_qodana_config_dir() {
    local base_dirs=()

    # Platform-specific Qodana cache locations
    if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        base_dirs+=("$HOME/AppData/Local/JetBrains/Qodana")
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        base_dirs+=("$HOME/Library/Caches/JetBrains/Qodana")
    else
        base_dirs+=("$HOME/.cache/JetBrains/Qodana")
    fi

    # Find most recently modified Qodana config directory
    local latest_dir=""
    local latest_time=0

    for base_dir in "${base_dirs[@]}"; do
        if [ -d "$base_dir" ]; then
            while IFS= read -r -d '' config_dir; do
                local mod_time=$(stat -c %Y "$config_dir" 2>/dev/null || stat -f %m "$config_dir" 2>/dev/null || echo 0)
                if [ "$mod_time" -gt "$latest_time" ]; then
                    latest_time=$mod_time
                    latest_dir="$config_dir"
                fi
            done < <(find "$base_dir" -mindepth 1 -maxdepth 1 -type d -name "*-*" -print0 2>/dev/null || true)
        fi
    done

    echo "$latest_dir"
}

# Extract SDK name from .idea/misc.xml
extract_sdk_name() {
    local misc_xml="$1"

    if [ ! -f "$misc_xml" ]; then
        log_warn "No .idea/misc.xml found at: $misc_xml"
        return 1
    fi

    # Extract project-jdk-name attribute
    local sdk_name=$(grep -oP 'project-jdk-name="\K[^"]+' "$misc_xml" 2>/dev/null || true)

    if [ -z "$sdk_name" ]; then
        log_warn "Could not extract SDK name from $misc_xml"
        return 1
    fi

    echo "$sdk_name"
}

# Detect Python paths from SDK name
detect_python_paths() {
    local sdk_name="$1"
    local project_root="$2"

    # Extract venv path if present
    local venv_path=""
    if [[ "$sdk_name" =~ virtualenv\ at\ (.+)$ ]]; then
        venv_path="${BASH_REMATCH[1]}"
        venv_path="${venv_path//\\//}"
    elif [[ "$sdk_name" =~ venv\ at\ (.+)$ ]]; then
        venv_path="${BASH_REMATCH[1]}"
        venv_path="${venv_path//\\//}"
    fi

    # If venv path is relative, resolve it
    if [ -n "$venv_path" ]; then
        if [[ "$venv_path" == .* ]] || [[ ! "$venv_path" =~ ^[A-Za-z]: ]]; then
            venv_path="$project_root/$venv_path"
        fi
    fi

    # Determine Python executable
    local python_exe=""
    if [ -n "$venv_path" ]; then
        if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            python_exe="$venv_path/Scripts/python.exe"
        else
            python_exe="$venv_path/bin/python"
        fi
    fi

    # Fallback to system Python
    if [ -z "$python_exe" ] || [ ! -f "$python_exe" ]; then
        python_exe=$(which python3 2>/dev/null || which python 2>/dev/null || echo "")
    fi

    if [ -z "$python_exe" ] || [ ! -f "$python_exe" ]; then
        log_error "Could not find Python executable"
        return 1
    fi

    # Get Python version
    local python_version=$("$python_exe" -c "import sys; print(f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null || echo "Python 3.11.0")

    # Determine library paths
    local site_packages=""
    local stdlib=""
    local dlls=""

    if [ -n "$venv_path" ]; then
        if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
            site_packages="$venv_path/Lib/site-packages"
            local base_python_dir=$(dirname $(dirname "$python_exe"))
            stdlib="$base_python_dir/Lib"
            dlls="$base_python_dir/DLLs"
        else
            site_packages="$venv_path/lib/python*/site-packages"
            stdlib="/usr/lib/python*"
            dlls="/usr/lib/python*/lib-dynload"
        fi
    else
        site_packages=$("$python_exe" -c "import site; print(site.getsitepackages()[0])" 2>/dev/null || echo "")
        stdlib=$("$python_exe" -c "import sys; print(sys.prefix + '/lib/python' + str(sys.version_info.major) + '.' + str(sys.version_info.minor))" 2>/dev/null || echo "")
        dlls=$("$python_exe" -c "import sys; print(sys.prefix + '/DLLs')" 2>/dev/null || echo "")
    fi

    # Convert Windows paths
    python_exe="${python_exe//\\//}"
    site_packages="${site_packages//\\//}"
    stdlib="${stdlib//\\//}"
    dlls="${dlls//\\//}"

    echo "$sdk_name"
    echo "$python_version"
    echo "$python_exe"
    echo "$site_packages"
    echo "$stdlib"
    echo "$dlls"
}

# Generate jdk.table.xml from template
generate_jdk_table() {
    local output_file="$1"
    local sdk_name="$2"
    local python_version="$3"
    local python_home="$4"
    local venv_site_packages="$5"
    local python_lib="$6"
    local python_dlls="$7"

    if [ ! -f "$TEMPLATE_FILE" ]; then
        log_error "Template file not found: $TEMPLATE_FILE"
        return 1
    fi

    # Read template and substitute placeholders
    local content=$(<"$TEMPLATE_FILE")
    content="${content//\{\{SDK_NAME\}\}/$sdk_name}"
    content="${content//\{\{PYTHON_VERSION\}\}/$python_version}"
    content="${content//\{\{PYTHON_HOME\}\}/$python_home}"
    content="${content//\{\{VENV_SITE_PACKAGES\}\}/$venv_site_packages}"
    content="${content//\{\{PYTHON_LIB\}\}/$python_lib}"
    content="${content//\{\{PYTHON_DLLS\}\}/$python_dlls}"

    # Ensure output directory exists
    mkdir -p "$(dirname "$output_file")"

    # Write generated content
    echo "$content" > "$output_file"

    log_success "Generated jdk.table.xml at: $output_file"
    return 0
}

# Main execution
main() {
    local project_root="${1:-.}"

    log_info "Checking for PyCharm platform fix requirement..."

    # Find Qodana config directory
    local qodana_config_dir=$(find_qodana_config_dir)

    if [ -z "$qodana_config_dir" ]; then
        log_warn "Qodana config directory not found. This fix only applies to native mode."
        return 0
    fi

    log_info "Qodana config directory: $qodana_config_dir"

    local jdk_table_file="$qodana_config_dir/config/options/jdk.table.xml"

    # Check if jdk.table.xml already exists
    if [ -f "$jdk_table_file" ]; then
        log_info "jdk.table.xml already exists. Skipping fix."
        return 0
    fi

    log_warn "jdk.table.xml not found. Applying fix..."

    # Extract SDK info from project
    local misc_xml="$project_root/.idea/misc.xml"
    local sdk_name=$(extract_sdk_name "$misc_xml")

    if [ -z "$sdk_name" ]; then
        log_error "Failed to extract SDK name from project"
        return 1
    fi

    log_info "Detected SDK: $sdk_name"

    # Detect Python paths (reading line by line to handle paths with spaces)
    local paths=()
    while IFS= read -r line; do
        paths+=("$line")
    done < <(detect_python_paths "$sdk_name" "$project_root")

    if [ ${#paths[@]} -lt 6 ]; then
        log_error "Failed to detect Python paths (got ${#paths[@]} values)"
        return 1
    fi

    local sdk_name_detected="${paths[0]}"
    local python_version="${paths[1]}"
    local python_home="${paths[2]}"
    local venv_site_packages="${paths[3]}"
    local python_lib="${paths[4]}"
    local python_dlls="${paths[5]}"

    log_info "Python version: $python_version"
    log_info "Python home: $python_home"
    log_info "Site packages: $venv_site_packages"

    # Generate jdk.table.xml
    if generate_jdk_table "$jdk_table_file" "$sdk_name_detected" "$python_version" "$python_home" "$venv_site_packages" "$python_lib" "$python_dlls"; then
        log_success "PyCharm platform fix applied successfully!"
        return 0
    else
        log_error "Failed to generate jdk.table.xml"
        return 1
    fi
}

# Run main with project root argument
main "$@"
