from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Set

from ..git.gitignore import GitIgnoreService


def read_text(path: Path) -> str:
    """Read file content with UTF-8 encoding, ignoring errors."""
    with path.open(encoding="utf-8", errors="ignore") as f:
        content = f.read()
    return content


def iter_files(
    root: Path,
    *,
    extensions: Set[str],
    gitignore_service: Optional[GitIgnoreService] = None,
    dir_pruner: Optional[Callable[[str], bool]] = None,
) -> Iterable[Path]:
    """
    Recursive file iterator with .gitignore and early directory pruning support.

    Args:
        root: Repository root directory
        extensions: Set of allowed file extensions (lowercase, with dot)
        gitignore_service: GitIgnore service for checking ignored paths
        dir_pruner: Optional callback for additional directory filtering

    Yields:
        Paths to files matching criteria
    """
    root = root.resolve()

    for dirpath, dirnames, filenames in os.walk(root):
        # Never enter .git directory
        if ".git" in dirnames:
            dirnames.remove(".git")

        # Calculate relative path for current directory
        current_rel = Path(dirpath).resolve().relative_to(root).as_posix()
        if current_rel == ".":
            current_rel = ""

        # Early pruning (in-place modification of dirnames)
        keep: List[str] = []
        for d in dirnames:
            if current_rel:
                rel_dir = f"{current_rel}/{d}"
            else:
                rel_dir = d

            # Check gitignore
            if gitignore_service and gitignore_service.is_dir_ignored(rel_dir):
                continue

            # Apply custom pruner
            if dir_pruner and not dir_pruner(rel_dir):
                continue

            keep.append(d)

        dirnames[:] = keep

        # Process files
        for fn in filenames:
            p = Path(dirpath, fn)

            # Check extension
            if p.suffix.lower() not in extensions:
                # Special names without suffix
                if p.name not in {"README", "Dockerfile", "Makefile", "pyproject.toml"}:
                    continue

            # Calculate relative path
            rel_posix = p.resolve().relative_to(root).as_posix()

            # Check gitignore
            if gitignore_service and gitignore_service.is_ignored(rel_posix):
                continue

            yield p
