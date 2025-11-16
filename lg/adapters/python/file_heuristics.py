"""
Python file heuristics for identifying trivial __init__.py files.
Separated into a dedicated module to simplify the main adapter.
"""

from __future__ import annotations

from ..context import LightweightContext


def is_trivial_init_file(lightweight_ctx: LightweightContext) -> bool:
    """
    Determine if __init__.py file is trivial.

    Triviality criteria:
    - empty file
    - only 'pass' / '...'
    - only re-export of public API (relative from-imports, __all__)

    Comments by themselves do NOT make file trivial (they may be useful).

    Args:
        lightweight_ctx: Lightweight context with file information

    Returns:
        True if file is trivial __init__.py
    """
    # Only for __init__.py
    if lightweight_ctx.filename != "__init__.py":
        return False

    text = lightweight_ctx.raw_text or ""
    stripped = text.strip()

    # Empty file is trivial
    if stripped == "":
        return True

    lines = text.splitlines()

    # Extract lines without blanks and comments for classification
    non_comment_lines = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("#"):
            # Comments are not counted in classification (they don't make file trivial)
            continue
        non_comment_lines.append(ln)

    # If file has only comments - NOT trivial
    if not non_comment_lines:
        return False

    def is_pass_or_ellipsis(s: str) -> bool:
        return s in ("pass", "...")

    def is_relative_from_import(s: str) -> bool:
        # from .pkg import X, Y
        if not s.startswith("from "):
            return False
        rest = s[5:].lstrip()
        return rest.startswith(".")

    def is_all_assign_start(s: str) -> bool:
        # __all__ = [...]
        return s.startswith("__all__")

    in_import_paren = False
    in_all_list = False

    for ln in non_comment_lines:
        if in_import_paren:
            # Continue until import group closes
            if ")" in ln:
                in_import_paren = False
            continue

        if in_all_list:
            # Allow multi-line list in __all__
            if "]" in ln:
                in_all_list = False
            continue

        if is_pass_or_ellipsis(ln):
            continue

        if is_relative_from_import(ln):
            # Allow multi-line imports with '('
            if ln.endswith("(") or ln.endswith("\\") or "(" in ln and ")" not in ln:
                in_import_paren = True
            continue

        if is_all_assign_start(ln):
            # Allow multi-line __all__ = [
            if "[" in ln and "]" not in ln:
                in_all_list = True
            continue

        # Any other construct makes file non-trivial
        return False

    # If we got here - all non-trivial lines are acceptable - file is trivial
    return True


def should_skip_python_file(lightweight_ctx: LightweightContext, skip_trivial_inits: bool) -> bool:
    """
    Determine if Python file should be skipped entirely.

    Args:
        lightweight_ctx: Lightweight context with file information
        skip_trivial_inits: Flag for skipping trivial __init__.py files

    Returns:
        True if file should be skipped
    """
    # Skip trivial __init__.py if the option is enabled
    if skip_trivial_inits:
        if is_trivial_init_file(lightweight_ctx):
            return True

    return False