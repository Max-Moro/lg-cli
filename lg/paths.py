"""
Path utilities for Listing Generator.

Single source of truth for configuration directory structure.
"""

from __future__ import annotations

from pathlib import Path

# Configuration directory name
CFG_DIR = "lg-cfg"
SECTIONS_FILE = "sections.yaml"


def cfg_root(root: Path) -> Path:
    """Absolute path to the lg-cfg/ directory."""
    return (root / CFG_DIR).resolve()


def is_cfg_relpath(s: str) -> bool:
    """
    Quick check whether a relative POSIX path belongs to the lg-cfg/ directory.
    Used in tree traversal pruners.
    """
    return s == CFG_DIR or s.startswith(CFG_DIR + "/")
