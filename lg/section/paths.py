from __future__ import annotations

from pathlib import Path
from typing import List

# Import shared constants from config.paths
from ..config.paths import cfg_root, SECTIONS_FILE


def sections_path(root: Path) -> Path:
    """Path to the main sections file lg-cfg/sections.yaml."""
    return cfg_root(root) / SECTIONS_FILE


def iter_section_fragments(root: Path) -> List[Path]:
    """
    All section fragment files: lg-cfg/**.sec.yaml (excluding the root sections.yaml).
    Returns a sorted list of absolute paths.
    """
    base = cfg_root(root)
    out: List[Path] = []
    for p in base.rglob("*.sec.yaml"):
        # Random namesake should not match the root sections.yaml
        if p.name == SECTIONS_FILE and p.parent == base:
            continue
        out.append(p)
    out.sort()
    return out


def iter_sections_yaml_files(root: Path) -> List[Path]:
    """
    Find all sections.yaml files in lg-cfg/ and its subdirectories.
    Returns a sorted list of absolute paths.

    This allows having sections.yaml in any subdirectory, not just in lg-cfg/ root.
    Sections from such files will have canonical IDs with directory prefix.

    Example:
        lg-cfg/sections.yaml -> sections have no prefix
        lg-cfg/adapters/sections.yaml -> sections have 'adapters/' prefix
    """
    base = cfg_root(root)
    out: List[Path] = []
    for p in base.rglob(SECTIONS_FILE):
        out.append(p)
    out.sort()
    return out


def canonical_fragment_prefix(root: Path, frag: Path) -> str:
    """
    For file lg-cfg/sub/pack.sec.yaml → canonical prefix 'sub/pack'
    (relative to lg-cfg/, POSIX).
    """
    base = cfg_root(root)
    rel = frag.resolve().relative_to(base.resolve()).as_posix()
    if not rel.endswith(".sec.yaml"):
        raise RuntimeError(f"Invalid fragment filename (expected *.sec.yaml): {frag}")
    return rel[: -len(".sec.yaml")]


def sections_yaml_prefix(root: Path, sections_file: Path) -> str:
    """
    Compute directory prefix for sections.yaml file.

    For lg-cfg/sections.yaml -> "" (no prefix, root level)
    For lg-cfg/adapters/sections.yaml -> "adapters"
    For lg-cfg/docs/api/sections.yaml -> "docs/api"

    Returns POSIX path relative to lg-cfg/.
    """
    base = cfg_root(root)
    # Parent directory of sections.yaml, relative to lg-cfg/
    parent_dir = sections_file.parent.resolve()

    if parent_dir == base.resolve():
        # Root level sections.yaml
        return ""

    # Subdirectory sections.yaml
    rel = parent_dir.relative_to(base.resolve()).as_posix()
    return rel
