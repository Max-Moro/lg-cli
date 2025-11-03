---
name: qodana-inspect
description: Run Qodana code inspection and get parsed results. Use when you need to analyze code quality, find unused code, detect potential bugs, or check for IntelliJ IDEA inspections. Returns structured list of problems grouped by file with severity, location, and code snippets.
---

# Qodana Code Inspector

This skill runs Qodana static analysis on the current project and returns parsed inspection results in an easy-to-read format.

## When to Use

Use this skill when you need to:
- Find code quality issues (unused code, redundant constructs, etc.)
- Detect potential bugs and problematic code patterns
- Check for IntelliJ IDEA inspections
- Get a list of issues to fix in the codebase
- Analyze code changes after modifications

## How to Use

### Basic Usage

Run full project inspection:

```bash
bash .claude/skills/qodana-inspect/scripts/run-qodana.sh
```

### Incremental Analysis

Analyze only changes since a specific commit:

```bash
bash .claude/skills/qodana-inspect/scripts/run-qodana.sh --diff-start <commit-hash>
```

## Output Format

The script returns results grouped by file:

```
=== FILE: src/main/kotlin/example/Example.kt ===

[HIGH] UnusedSymbol
Location: line 45, column 13
Message: Variable 'unusedVar' is never used
Code:
val unusedVar = "test"

---

[MODERATE] NamingConvention
Location: line 52, column 9
Message: Property name should follow naming convention
Code:
private val MyProperty = "value"

=== FILE: src/main/kotlin/example/Another.kt ===
...
```

## Severity Levels

- **HIGH**: Important issues (unused code, potential bugs, API problems)
- **MODERATE**: Style and convention issues
- **INFO**: Informational notices

## Technical Details

- **Linter**: qodana-jvm-community (Qodana Community for JVM)
- **Mode**: Native (no Docker required)
- **Output**: Parsed SARIF JSON format
- **Results location**: `~/AppData/Local/JetBrains/Qodana/*/results/`

## Requirements

- Qodana CLI must be installed (`qodana` command available)
- `jq` must be installed for JSON parsing
- Project must be a valid Kotlin/JVM project

## Notes

- Full scan takes ~30 seconds
- Incremental scan with `--diff-start` takes ~3 minutes (analyzes two project states)
- Results include exact line/column numbers and code snippets for context
- Script filters out Qodana progress messages, showing only final results

## Limitations

- Quick-Fix auto-correction is not available in Community Edition
- You must manually fix identified issues using Edit tool
- Use code context and snippets provided in output to understand and fix problems
