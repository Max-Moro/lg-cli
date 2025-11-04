#!/bin/bash

# Qodana Inspector Script
# Runs Qodana analysis and parses results into a readable format
# Supports all JetBrains Qodana linters for various programming languages

set -euo pipefail

# Default Configuration
LINTER=""
RESULTS_DIR=""

# Auto-detect results directory based on OS
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
    # Windows (Git Bash, MSYS2, Cygwin)
    RESULTS_DIR="$HOME/AppData/Local/JetBrains/Qodana"
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    RESULTS_DIR="$HOME/Library/Caches/JetBrains/Qodana"
else
    # Linux and other Unix-like systems
    RESULTS_DIR="$HOME/.cache/JetBrains/Qodana"
fi

# Colors for output (optional, can be disabled)
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to display usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Runs Qodana static analysis and returns parsed results.

OPTIONS:
    --linter LINTER          Specify Qodana linter to use (required)
    --diff-start COMMIT      Analyze only changes since specified commit
    --results-dir DIR        Custom results directory (auto-detected by default)
    -h, --help               Show this help message

AVAILABLE LINTERS:
    JVM Ecosystem:
        qodana-jvm-community         Java, Kotlin, Groovy (Community)
        qodana-jvm                   Java, Kotlin, Groovy (Ultimate)
        qodana-jvm-android           Android (Community)
        qodana-android               Android (Ultimate)

    Web Development:
        qodana-js                    JavaScript, TypeScript (Ultimate)
        qodana-php                   PHP, JavaScript, TypeScript (Ultimate)

    .NET & C/C++:
        qodana-cdnet                 C#, VB.NET (Community)
        qodana-dotnet                C#, VB.NET, C, C++ (Ultimate)
        qodana-clang                 C, C++ (Community)
        qodana-cpp                   C, C++ (Ultimate)

    Other Languages:
        qodana-python-community      Python (Community)
        qodana-python                Python (Ultimate)
        qodana-go                    Go (Ultimate)
        qodana-ruby                  Ruby (Ultimate)

EXAMPLES:
    # Kotlin/Java project
    $0 --linter qodana-jvm-community

    # TypeScript project
    $0 --linter qodana-js

    # Python project with incremental analysis
    $0 --linter qodana-python-community --diff-start HEAD~1

EOF
    exit 0
}

# Parse arguments
DIFF_MODE=false
DIFF_START=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --linter)
            LINTER="$2"
            shift 2
            ;;
        --diff-start)
            DIFF_MODE=true
            DIFF_START="$2"
            shift 2
            ;;
        --results-dir)
            RESULTS_DIR="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate required arguments
if [ -z "$LINTER" ]; then
    echo -e "${RED}Error: --linter is required${NC}" >&2
    echo "Use --help to see available linters" >&2
    exit 1
fi

# Run Qodana
echo -e "${GREEN}Running Qodana inspection with linter: ${LINTER}${NC}" >&2
echo "" >&2

# Check if qodana.yaml exists in the project root
QODANA_CONFIG=""
if [ -f "qodana.yaml" ]; then
    echo "Found qodana.yaml configuration file" >&2
    QODANA_CONFIG="--config=qodana.yaml"
fi

if [ "$DIFF_MODE" = true ] && [ -n "$DIFF_START" ]; then
    echo "Analyzing changes since: $DIFF_START" >&2
    qodana scan --linter "$LINTER" --within-docker=false --diff-start="$DIFF_START" --save-report=false $QODANA_CONFIG 2>&1 | grep -E "(Analysis results:|problems detected|problems count|new problems)" >&2 || true
else
    echo "Running full project analysis..." >&2
    qodana scan --linter "$LINTER" --within-docker=false --save-report=false $QODANA_CONFIG 2>&1 | grep -E "(Analysis results:|problems detected|problems count)" >&2 || true
fi

echo "" >&2
echo "Parsing results..." >&2

# Find the most recent results directory
LATEST_RESULTS=$(find "$RESULTS_DIR" -maxdepth 2 -name "results" -type d | sort -r | head -1)

if [ -z "$LATEST_RESULTS" ]; then
    echo "Error: No results directory found" >&2
    exit 1
fi

SARIF_FILE="$LATEST_RESULTS/qodana.sarif.json"

if [ ! -f "$SARIF_FILE" ]; then
    echo "Error: SARIF file not found at $SARIF_FILE" >&2
    exit 1
fi

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed" >&2
    exit 1
fi

# Parse SARIF and output in a structured format
jq -r '
.runs[0].results // [] |
group_by(.locations[0].physicalLocation.artifactLocation.uri) |
map({
  file: .[0].locations[0].physicalLocation.artifactLocation.uri,
  problems: map({
    ruleId: .ruleId,
    severity: (if .level == "warning" then "HIGH" elif .level == "note" then "MODERATE" else "INFO" end),
    message: .message.text,
    line: .locations[0].physicalLocation.region.startLine,
    column: .locations[0].physicalLocation.region.startColumn,
    snippet: .locations[0].physicalLocation.region.snippet.text,
    context: .locations[0].physicalLocation.contextRegion.snippet.text
  })
}) |
map("
=== FILE: \(.file) ===
\(.problems | map("
[\(.severity)] \(.ruleId)
Location: line \(.line), column \(.column)
Message: \(.message)
Code:
\(.snippet)
") | join("\n---\n"))
") | join("\n\n")
' "$SARIF_FILE"

# Summary
TOTAL_PROBLEMS=$(jq -r '.runs[0].results | length' "$SARIF_FILE")
echo "" >&2
echo "Total problems found: $TOTAL_PROBLEMS" >&2
