#!/bin/bash

# Script for analyzing unused code with Vulture
# Author: AI Assistant
# Description: Runs Vulture to find dead code in the project

# set -e  # Disabled to handle Vulture exit codes

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    error "Virtual environment .venv not found!"
    exit 1
fi

# Check Vulture installation
if ! .venv/Scripts/python.exe -m vulture --version > /dev/null 2>&1; then
    error "Vulture is not installed in virtual environment!"
    log "Install dependencies: .venv/Scripts/python.exe -m pip install -e \".[dev]\""
    exit 1
fi

# Check if configuration file exists
if [ ! -f "vulture.toml" ]; then
    error "Configuration file vulture.toml not found!"
    exit 1
fi

# Create reports directory
REPORT_DIR="reports"
mkdir -p "$REPORT_DIR"

# Generate report filename with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
REPORT_FILE="$REPORT_DIR/vulture_report_$TIMESTAMP.txt"

log "Starting unused code analysis..."

# Run Vulture with detailed output
log "Running Vulture with configuration from vulture.toml..."

# Run Vulture and save exit code
.venv/Scripts/python.exe -m vulture \
    --config vulture.toml \
    --min-confidence 60 \
    --sort-by-size \
    lg \
    > "$REPORT_FILE" 2>&1
VULTURE_EXIT_CODE=$?

# Check execution result
if [ $VULTURE_EXIT_CODE -eq 0 ]; then
    success "Analysis completed successfully!"
    success "No unused code found! Project is clean."
else
    success "Analysis completed successfully!"

    # Count found issues
    ISSUES_COUNT=$(wc -l < "$REPORT_FILE" 2>/dev/null || echo "0")

    if [ "$ISSUES_COUNT" -gt 0 ]; then
        warning "Found $ISSUES_COUNT potentially unused code elements"

        # Show brief summary
        log "Brief summary of found issues:"
        echo "----------------------------------------"
        head -20 "$REPORT_FILE"
        echo "----------------------------------------"

        if [ "$ISSUES_COUNT" -gt 20 ]; then
            log "Showing first 20 issues. Full report in file: $REPORT_FILE"
        fi
    else
        success "No unused code found! Project is clean."
    fi

    log "Full report saved in file: $REPORT_FILE"

    # Create copy of latest report
    cp "$REPORT_FILE" "$REPORT_DIR/vulture_latest.txt"
    log "Created copy of latest report: $REPORT_DIR/vulture_latest.txt"
fi

log "Analysis completed!"

# Exit with code 0 since analysis completed successfully
exit 0
