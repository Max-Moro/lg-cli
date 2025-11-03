#!/bin/bash

# Qodana Inspector Script
# Runs Qodana analysis and parses results into a readable format

set -euo pipefail

# Configuration
LINTER="qodana-jvm-community"
RESULTS_DIR="$HOME/AppData/Local/JetBrains/Qodana"

# Colors for output (optional, can be disabled)
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Parse arguments
DIFF_MODE=false
DIFF_START=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --diff-start)
            DIFF_MODE=true
            DIFF_START="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run Qodana
echo "Running Qodana inspection..." >&2

if [ "$DIFF_MODE" = true ] && [ -n "$DIFF_START" ]; then
    qodana scan --linter "$LINTER" --within-docker=false --diff-start="$DIFF_START" --save-report=false 2>&1 | grep -E "(Analysis results:|problems detected|problems count|new problems)" >&2 || true
else
    qodana scan --linter "$LINTER" --within-docker=false --save-report=false 2>&1 | grep -E "(Analysis results:|problems detected|problems count)" >&2 || true
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
