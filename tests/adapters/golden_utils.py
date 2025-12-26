"""
Utilities for golden tests of language adapters.
Provides unified work with golden reference files.
"""

import os
from pathlib import Path
from typing import Optional

import pytest


def _get_language_extensions(language: str) -> list[str]:
    """
    Returns the file extensions for a given language.

    Args:
        language: Language name ("python", "typescript", etc.)

    Returns:
        list[str]: File extensions with dots, primary extension first
    """
    extension_map = {
        "python": [".py"],
        "typescript": [".ts", ".tsx"],
        "javascript": [".js", ".jsx", ".mjs", ".cjs"],
        "java": [".java"],
        "csharp": [".cs"],
        "cpp": [".cpp", ".hpp", ".cc", ".hh", ".cxx", ".hxx"],
        "c": [".c", ".h"],
        "go": [".go"],
        "rust": [".rs"],
        "swift": [".swift"],
        "kotlin": [".kt", ".kts"],
        "scala": [".scala"],
        "php": [".php"],
        "ruby": [".rb"],
        "perl": [".pl"],
        "shell": [".sh"],
        "powershell": [".ps1"],
        "html": [".html"],
        "css": [".css"],
        "scss": [".scss"],
        "sass": [".sass"],
        "xml": [".xml"],
        "json": [".json"],
        "yaml": [".yaml", ".yml"],
        "toml": [".toml"],
        "markdown": [".md"],
    }

    return extension_map.get(language, [".txt"])


def _get_language_extension(language: str) -> str:
    """
    Returns the primary file extension for a given language.

    Args:
        language: Language name ("python", "typescript", etc.)

    Returns:
        str: Primary file extension with a dot (".py", ".ts", etc.)
    """
    return _get_language_extensions(language)[0]


def assert_golden_match(
    result: str,
    optimization_type: str,
    golden_name: str,
    language: Optional[str] = None,
    update_golden: Optional[bool] = None
) -> None:
    """
    Generic function for comparing results with golden files.

    Args:
        result: Actual result to compare
        optimization_type: Type of optimization ("function_bodies", "complex", "comments", etc.)
        golden_name: Golden file name (without extension)
        language: Adapter language ("python", "typescript", etc.).
                 If not specified, detected automatically from test context
        update_golden: Flag to update golden file.
                      If None, taken from PYTEST_UPDATE_GOLDENS environment variable

    Raises:
        AssertionError: If result does not match the reference
    """
    # Detect language automatically if not specified
    if language is None:
        language = _detect_language_from_test_context()

    # Determine update flag
    if update_golden is None:
        update_golden = os.getenv("PYTEST_UPDATE_GOLDENS") == "1"

    # Form path to golden file
    golden_file = _get_golden_file_path(language, optimization_type, golden_name)

    # Normalize result for stability
    normalized_result = _normalize_result(result)

    # Comparison/update logic
    if update_golden or not golden_file.exists():
        golden_file.parent.mkdir(parents=True, exist_ok=True)
        golden_file.write_text(normalized_result, encoding='utf-8')
        if update_golden:
            pytest.skip(f"Updated golden file: {golden_file}")

    expected = golden_file.read_text(encoding='utf-8')
    if normalized_result != expected:
        # Create informative error message
        diff_msg = _create_diff_message(expected, normalized_result, golden_file)
        raise AssertionError(diff_msg)


def _detect_language_from_test_context() -> str:
    """
    Detects adapter language from the current test context.
    Analyzes the path to the test file.
    """
    import inspect

    # Get call stack and look for test file
    for frame_info in inspect.stack():
        frame_path = Path(frame_info.filename)

        # Look for pattern tests/adapters/<language>/test_*.py
        if (frame_path.name.startswith("test_") and
            frame_path.suffix == ".py" and
            "adapters" in frame_path.parts):

            parts = frame_path.parts
            try:
                adapters_idx = parts.index("adapters")
                if adapters_idx + 1 < len(parts):
                    language = parts[adapters_idx + 1]
                    # Check that this is actually a language (not __pycache__ etc.)
                    if language not in ("__pycache__", "__init__.py") and not language.startswith("."):
                        return language
            except ValueError:
                continue

    # Fallback: try to extract from test module name
    test_module = inspect.getmodule(inspect.stack()[2].frame)
    if test_module and test_module.__name__:
        module_parts = test_module.__name__.split('.')
        for i, part in enumerate(module_parts):
            if part == "adapters" and i + 1 < len(module_parts):
                return module_parts[i + 1]

    raise ValueError(
        "Cannot auto-detect language for golden test. "
        "Please specify language parameter explicitly, or ensure test is in "
        "tests/adapters/<language>/ directory structure."
    )


def _get_golden_file_path(language: str, optimization_type: str, golden_name: str) -> Path:
    """
    Forms path to golden file for given language, optimization type and name.

    Args:
        language: Language name ("python", "typescript", etc.)
        optimization_type: Type of optimization ("function_bodies", "complex", "comments", etc.)
        golden_name: File name without extension

    Returns:
        Path to golden file
    """
    # Find project root (where pyproject.toml exists)
    current = Path(__file__)
    while current.parent != current:
        if (current / "pyproject.toml").exists():
            break
        current = current.parent
    else:
        # Fallback: from current file upward
        current = Path(__file__).parent.parent.parent

    # Get language extension
    extension = _get_language_extension(language)

    golden_dir = current / "tests" / "adapters" / language / "goldens" / optimization_type
    return golden_dir / f"{golden_name}{extension}"


def _normalize_result(result: str) -> str:
    """
    Normalizes result for stable comparison.

    Args:
        result: Original result

    Returns:
        Normalized result
    """
    # Normalize line endings
    normalized = result.replace('\r\n', '\n').replace('\r', '\n')

    # Remove trailing whitespace at end of file, but preserve structure
    normalized = normalized.rstrip() + '\n' if normalized.strip() else ''

    return normalized


def _create_diff_message(expected: str, actual: str, golden_file: Path) -> str:
    """
    Creates informative message about differences for AssertionError.

    Args:
        expected: Expected content
        actual: Actual content
        golden_file: Path to golden file

    Returns:
        Formatted message with diff
    """
    import difflib

    # Create unified diff
    diff_lines = list(difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile=f"expected ({golden_file.name})",
        tofile="actual",
        lineterm=""
    ))

    if len(diff_lines) > 50:  # Limit very long diffs
        diff_lines = diff_lines[:25] + ["\n... (diff truncated, showing first 25 lines) ...\n"] + diff_lines[-25:]

    diff_text = "".join(diff_lines)

    return (
        f"Golden test failed for {golden_file}\n"
        f"To update the golden file, run:\n"
        f"  PYTEST_UPDATE_GOLDENS=1 python -m pytest {golden_file.stem}\n"
        f"\nDiff:\n{diff_text}"
    )


def get_golden_dir(language: str, optimization_type: Optional[str] = None) -> Path:
    """
    Gets directory for golden files of given language and optimization type.
    Can be useful for external scripts.

    Args:
        language: Language name
        optimization_type: Optimization type. If None, returns base goldens directory

    Returns:
        Path to directory with golden files
    """
    if optimization_type is None:
        # Return base goldens directory
        current = Path(__file__)
        while current.parent != current:
            if (current / "pyproject.toml").exists():
                break
            current = current.parent
        else:
            current = Path(__file__).parent.parent.parent
        return current / "tests" / "adapters" / language / "goldens"
    else:
        return _get_golden_file_path(language, optimization_type, "dummy").parent


def list_golden_files(language: Optional[str] = None, optimization_type: Optional[str] = None) -> list[Path]:
    """
    Returns list of all golden files for language and/or optimization type.

    Args:
        language: Language name or None for all languages
        optimization_type: Optimization type or None for all types

    Returns:
        List of paths to golden files
    """
    result = []

    if language:
        # Specific language
        base_golden_dir = get_golden_dir(language)
        if not base_golden_dir.exists():
            return []

        if optimization_type:
            # Specific optimization type
            opt_dir = base_golden_dir / optimization_type
            if opt_dir.exists():
                # Look for files with language extensions
                extension = _get_language_extension(language)
                result.extend(opt_dir.glob(f"*{extension}"))
        else:
            # All optimization types for language (excluding do/)
            for opt_dir in base_golden_dir.iterdir():
                if opt_dir.is_dir() and opt_dir.name != "do":
                    extension = _get_language_extension(language)
                    result.extend(opt_dir.glob(f"*{extension}"))
    else:
        # All languages
        adapters_dir = Path(__file__).parent
        for lang_dir in adapters_dir.iterdir():
            if lang_dir.is_dir() and not lang_dir.name.startswith(("_", ".")):
                lang_name = lang_dir.name
                goldens_dir = lang_dir / "goldens"
                if goldens_dir.exists():
                    if optimization_type:
                        # Specific optimization type for all languages
                        opt_dir = goldens_dir / optimization_type
                        if opt_dir.exists():
                            extension = _get_language_extension(lang_name)
                            result.extend(opt_dir.glob(f"*{extension}"))
                    else:
                        # All optimization types for all languages (excluding do/)
                        for opt_dir in goldens_dir.iterdir():
                            if opt_dir.is_dir() and opt_dir.name != "do":
                                extension = _get_language_extension(lang_name)
                                result.extend(opt_dir.glob(f"*{extension}"))

    return result


def load_sample_code(sample_name: str, language: Optional[str] = None) -> str:
    """
    Loads source code from file in goldens/do/ directory.

    Args:
        sample_name: Sample file name (without extension)
        language: Adapter language. If not specified, detected automatically

    Returns:
        str: Content of source code file

    Raises:
        FileNotFoundError: If file not found
    """
    if language is None:
        language = _detect_language_from_test_context()

    sample_file = _get_sample_file_path(language, sample_name)

    if not sample_file.exists():
        raise FileNotFoundError(
            f"Sample file not found: {sample_file}\n"
            f"Expected location: tests/adapters/{language}/goldens/do/{sample_name}"
            f"{_get_language_extension(language)}"
        )

    return sample_file.read_text(encoding='utf-8')


def _get_sample_file_path(language: str, sample_name: str) -> Path:
    """
    Forms path to source code file for given language and name.
    Searches through all possible extensions for the language.

    Args:
        language: Language name ("python", "typescript", etc.)
        sample_name: File name without extension

    Returns:
        Path to source code file (existing file or primary extension path)
    """
    # Find project root (where pyproject.toml exists)
    current = Path(__file__)
    while current.parent != current:
        if (current / "pyproject.toml").exists():
            break
        current = current.parent
    else:
        # Fallback: from current file upward
        current = Path(__file__).parent.parent.parent

    sample_dir = current / "tests" / "adapters" / language / "goldens" / "do"

    # Try all possible extensions for the language
    for ext in _get_language_extensions(language):
        candidate = sample_dir / f"{sample_name}{ext}"
        if candidate.exists():
            return candidate

    # Return path with primary extension (for error messages)
    return sample_dir / f"{sample_name}{_get_language_extension(language)}"


def list_sample_files(language: Optional[str] = None) -> list[Path]:
    """
    Returns list of all source data files for language or all languages.

    Args:
        language: Language name or None for all languages

    Returns:
        List of paths to source data files
    """
    result = []

    if language:
        # Specific language
        sample_dir = _get_sample_file_path(language, "dummy").parent
        if sample_dir.exists():
            for ext in _get_language_extensions(language):
                result.extend(sample_dir.glob(f"*{ext}"))
    else:
        # All languages
        adapters_dir = Path(__file__).parent
        for lang_dir in adapters_dir.iterdir():
            if lang_dir.is_dir() and not lang_dir.name.startswith(("_", ".")):
                lang_name = lang_dir.name
                sample_dir = lang_dir / "goldens" / "do"
                if sample_dir.exists():
                    for ext in _get_language_extensions(lang_name):
                        result.extend(sample_dir.glob(f"*{ext}"))

    return result
