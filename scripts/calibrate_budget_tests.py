#!/usr/bin/env python3
"""
Script to calibrate BUDGET_STEPS constants in budget tests.

This script runs the budget system with minimal threshold to collect
full metrics, then calculates appropriate budget step thresholds for testing.

Usage:
    python scripts/calibrate_budget_tests.py [LANGUAGES] [UPDATE_FILES]

Arguments:
    LANGUAGES      - Comma-separated list of languages or 'all' (default: all)
    UPDATE_FILES   - 'true' to update test files, 'false' for dry-run (default: false)

Examples:
    python scripts/calibrate_budget_tests.py                     # Preview all languages (dry-run)
    python scripts/calibrate_budget_tests.py all true            # Update all languages
    python scripts/calibrate_budget_tests.py python              # Preview Python only
    python scripts/calibrate_budget_tests.py python true         # Update Python
    python scripts/calibrate_budget_tests.py python,typescript   # Preview multiple languages
    python scripts/calibrate_budget_tests.py python,java true    # Update multiple languages
"""

from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from lg.adapters.code_model import BudgetConfig


# Supported languages with budget tests
SUPPORTED_LANGUAGES = [
    "python",
    "typescript",
    "javascript",
    "java",
    "kotlin",
    "cpp",
    "c",
    "scala",
    "go",
    "rust",
]


def import_language_utils(language: str):
    """
    Dynamically import test utils for a language.

    Returns:
        Tuple of (make_adapter, lctx, load_sample_code, cfg_class)
    """
    # Import language-specific utilities
    utils_module = importlib.import_module(f"tests.adapters.{language}.utils")
    make_adapter = getattr(utils_module, "make_adapter")
    lctx = getattr(utils_module, "lctx")

    # Import golden utils
    golden_utils = importlib.import_module("tests.adapters.golden_utils")
    load_sample_code = getattr(golden_utils, "load_sample_code")

    # Import config class
    # Map language to config class name
    cfg_class_map = {
        "python": "PythonCfg",
        "typescript": "TypeScriptCfg",
        "javascript": "JavaScriptCfg",
        "java": "JavaCfg",
        "kotlin": "KotlinCfg",
        "cpp": "CppCfg",
        "c": "CCfg",
        "scala": "ScalaCfg",
        "go": "GoCfg",
        "rust": "RustCfg",
    }

    cfg_class_name = cfg_class_map.get(language)
    if not cfg_class_name:
        raise ValueError(f"Unknown language: {language}")

    adapter_module = importlib.import_module(f"lg.adapters.{language}")
    cfg_class = getattr(adapter_module, cfg_class_name)

    return make_adapter, lctx, load_sample_code, cfg_class


def calibrate_budget_steps(language: str) -> Tuple[List[int], Dict[str, int]]:
    """
    Calibrate budget steps for a language.

    Returns:
        Tuple of (budget_steps, raw_metrics)
    """
    print(f"\n=== Calibrating {language} ===")

    # Import language utilities
    make_adapter, lctx, load_sample_code, cfg_class = import_language_utils(language)

    # Load sample code using golden_utils
    code = load_sample_code("complex", language=language)

    # Create config with minimal budget to trigger all steps
    cfg = cfg_class()
    cfg.budget = BudgetConfig(max_tokens_per_file=1)  # Minimal to trigger all steps
    cfg.placeholders.style = "none"

    # Create adapter with real tokenizer
    adapter = make_adapter(cfg)

    # Create lightweight context
    context = lctx(code)

    # Process to get full metrics
    _, meta = adapter.process(context)

    # Extract budget metrics
    prefix = f"{language}.budget"
    metrics = {k.replace(prefix + ".", ""): v for k, v in meta.items() if k.startswith(prefix)}

    print(f"Metrics collected: {len(metrics)} keys")
    for key, value in sorted(metrics.items()):
        print(f"  {key}: {value}")

    # Calculate budget steps
    tokens_before = metrics.get("tokens_before", 0)
    tokens_after = metrics.get("tokens_after", 0)

    # Standard step order (from budget.md)
    step_order = [
        "imports_external",
        "literals",
        "comments",
        "imports_local",
        "private_bodies",
        "public_api_only",
        "public_bodies",
        "docstrings_first_sentence",
    ]

    # Calculate cumulative thresholds
    budget_steps = []

    # First step: no optimizations (baseline)
    baseline = tokens_before + 1
    budget_steps.append(baseline)
    print(f"  Baseline (no optimizations): threshold={baseline}")

    # Cumulative optimization steps
    cumulative_savings = 0
    for step in step_order:
        step_key = f"steps.{step}"
        savings = metrics.get(step_key, 0)

        if savings > 0:
            cumulative_savings += savings
            threshold = tokens_before - cumulative_savings + 1
            budget_steps.append(threshold)
            print(f"  Step '{step}': savings={savings}, cumulative={cumulative_savings}, threshold={threshold}")

    # Final step: use tokens_after only if it's significantly different from last step
    # (difference should be at least 5 tokens to avoid duplicates)
    if budget_steps and abs(budget_steps[-1] - tokens_after) > 5:
        budget_steps.append(tokens_after)
        print(f"  Final (all optimizations): threshold={tokens_after}")

    return budget_steps, metrics


def cleanup_old_goldens(language: str, dry_run: bool = False) -> int:
    """
    Remove old golden files with obsolete budget thresholds.

    Args:
        language: Language name
        dry_run: If True, only show what would be deleted

    Returns:
        Number of files that were (or would be) deleted
    """
    # Get language extension
    extension_map = {
        "python": ".py",
        "typescript": ".ts",
        "javascript": ".js",
        "java": ".java",
        "kotlin": ".kt",
        "cpp": ".cpp",
        "c": ".c",
        "scala": ".scala",
        "go": ".go",
        "rust": ".rs",
    }
    ext = extension_map.get(language, ".txt")

    # Path to budget goldens directory
    goldens_dir = PROJECT_ROOT / "tests" / "adapters" / language / "goldens" / "budget"

    if not goldens_dir.exists():
        return 0

    # Find all complex_budget_*.ext files
    pattern = f"complex_budget_*{ext}"
    old_files = list(goldens_dir.glob(pattern))

    if not old_files:
        return 0

    if dry_run:
        print(f"  [DRY RUN] Would delete {len(old_files)} old golden file(s):")
        for f in old_files:
            print(f"    - {f.name}")
    else:
        print(f"  🗑️  Cleaning up {len(old_files)} old golden file(s)...")
        for f in old_files:
            f.unlink()
            print(f"    Deleted: {f.name}")

    return len(old_files)


def update_test_file(language: str, budget_steps: List[int], dry_run: bool = False) -> None:
    """Update BUDGET_STEPS constant in test file."""
    test_file = PROJECT_ROOT / "tests" / "adapters" / language / "test_budget.py"

    if not test_file.exists():
        print(f"  ⚠️  Test file not found: {test_file}")
        return

    content = test_file.read_text(encoding="utf-8")

    # Pattern to match BUDGET_STEPS = [...]
    pattern = r"^BUDGET_STEPS\s*=\s*\[.*?\]"
    replacement = f"BUDGET_STEPS = {budget_steps}"

    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)

    if new_content == content:
        print(f"  ⚠️  Could not find BUDGET_STEPS in {test_file}")
        return

    if dry_run:
        print(f"  [DRY RUN] Would update BUDGET_STEPS in {test_file}")
        print(f"    New value: {budget_steps}")
    else:
        test_file.write_text(new_content, encoding="utf-8")
        print(f"  ✓ Updated BUDGET_STEPS in {test_file}")
        print(f"    New value: {budget_steps}")


def validate_languages(languages_arg: str) -> List[str]:
    """
    Validate and expand language argument.

    Args:
        languages_arg: 'all' or comma-separated list of languages

    Returns:
        List of validated language names
    """
    if languages_arg == "all":
        return SUPPORTED_LANGUAGES

    # Parse comma-separated list
    languages = [lang.strip() for lang in languages_arg.split(",")]

    # Validate each language
    validated = []
    for lang in languages:
        if lang in SUPPORTED_LANGUAGES:
            validated.append(lang)
        else:
            print(f"Warning: Unknown language '{lang}' (skipping)")

    if not validated:
        print("Error: No valid languages specified.")
        print(f"Available languages: {', '.join(SUPPORTED_LANGUAGES)}")
        sys.exit(1)

    return validated


def print_usage():
    """Print usage information."""
    print(f"""Usage: {sys.argv[0]} [LANGUAGES] [UPDATE_FILES]

Arguments:
  LANGUAGES      - Comma-separated list of languages or 'all' (default: all)
  UPDATE_FILES   - 'true' to update test files, 'false' for dry-run (default: false)

Available languages:
  {', '.join(SUPPORTED_LANGUAGES)}

Examples:
  # Preview all languages (dry-run)
  {sys.argv[0]}

  # Update all languages
  {sys.argv[0]} all true

  # Preview Python only
  {sys.argv[0]} python

  # Update Python
  {sys.argv[0]} python true

  # Preview multiple languages
  {sys.argv[0]} python,typescript

  # Update multiple languages
  {sys.argv[0]} python,java true
""")


def main():
    """Main entry point."""
    # Parse arguments
    languages_arg = sys.argv[1] if len(sys.argv) > 1 else "all"
    update_files_arg = sys.argv[2] if len(sys.argv) > 2 else "false"

    # Show help if requested
    if languages_arg in ("-h", "--help", "help"):
        print_usage()
        sys.exit(0)

    # Validate languages
    languages = validate_languages(languages_arg)

    # Parse update_files flag
    update_files = update_files_arg.lower() in ("true", "1", "yes")
    dry_run = not update_files

    print("=" * 70)
    print("Budget Test Calibration Script")
    print("=" * 70)
    print(f"Languages to calibrate: {', '.join(languages)}")
    print(f"Mode: {'UPDATE' if update_files else 'DRY RUN (preview only)'}")
    print("")

    # Calibrate each language
    results = {}
    for language in languages:
        try:
            budget_steps, metrics = calibrate_budget_steps(language)
            results[language] = (budget_steps, metrics)

            # Clean up old golden files before updating test file
            cleanup_old_goldens(language, dry_run=dry_run)

            # Update BUDGET_STEPS constant
            update_test_file(language, budget_steps, dry_run=dry_run)
        except Exception as e:
            print(f"  ❌ Error calibrating {language}: {e}")
            import traceback
            traceback.print_exc()

    # Summary
    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)

    for language, (budget_steps, metrics) in results.items():
        tokens_before = metrics.get("tokens_before", 0)
        tokens_after = metrics.get("tokens_after", 0)
        print(f"\n{language}:")
        print(f"  Tokens before: {tokens_before}")
        print(f"  Tokens after: {tokens_after}")
        print(f"  Budget steps ({len(budget_steps)}): {budget_steps}")

    print("\n✓ Calibration complete!")
    if update_files:
        print(f"\n⚠️  Old golden files were cleaned up.")
        print(f"Next steps:")
        print(f"  1. Generate new golden files:")
        if languages_arg == "all":
            print(f"     ./scripts/test_adapters.sh budget all true")
        else:
            print(f"     ./scripts/test_adapters.sh budget {languages_arg} true")
        print(f"  2. Verify tests pass:")
        if languages_arg == "all":
            print(f"     ./scripts/test_adapters.sh budget all")
        else:
            print(f"     ./scripts/test_adapters.sh budget {languages_arg}")
    else:
        print(f"\nTo apply changes, run:")
        print(f"  {sys.argv[0]} {languages_arg} true")


if __name__ == "__main__":
    main()
