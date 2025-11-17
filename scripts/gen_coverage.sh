#!/bin/bash

# Script for generating HTML test coverage report
# Author: AI Assistant
# Description: Runs pytest with coverage and generates HTML report in htmlcov/ folder

set -e

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
    log "Create virtual environment: python -m venv .venv"
    exit 1
fi

# Determine Python path based on OS
if [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
else
    error "Could not find Python interpreter in .venv!"
    exit 1
fi

log "Using Python: $PYTHON"

# Check pytest and coverage installation
if ! $PYTHON -m pytest --version > /dev/null 2>&1; then
    error "pytest is not installed in virtual environment!"
    log "Install dependencies: $PYTHON -m pip install -e \".[dev]\""
    exit 1
fi

if ! $PYTHON -m pip show coverage > /dev/null 2>&1; then
    warning "coverage is not installed, installing..."
    $PYTHON -m pip install coverage pytest-cov
fi

log "Removing old coverage data..."
rm -rf .coverage htmlcov/

log "Running tests with coverage measurement..."
$PYTHON -m pytest --cov=lg --cov-report=html --cov-report=term tests/

# Check execution success
if [ $? -eq 0 ]; then
    success "Tests completed successfully!"

    if [ -d "htmlcov" ]; then
        success "HTML coverage report generated in htmlcov/ folder"
        log "Open htmlcov/index.html in browser to view the report"
    else
        warning "htmlcov folder was not created"
    fi
else
    error "Errors occurred during test execution"
    exit 1
fi
