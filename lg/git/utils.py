"""
Low-level Git utilities.

Contains helper functions for executing git commands
and parsing their output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional


def run_git(root: Path, args: List[str]) -> List[str]:
    """
    Execute a git command and return output lines.

    Args:
        root: Repository root directory
        args: Git command arguments (without 'git' prefix)

    Returns:
        List of non-empty output lines, or empty list on error
    """
    try:
        out = subprocess.check_output(
            ["git", "-C", str(root), *args],
            text=True,
            encoding="utf-8",
            errors="ignore",
            stderr=subprocess.DEVNULL
        )
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


def find_merge_base(root: Path, target_branch: Optional[str]) -> Optional[str]:
    """
    Find the base point for comparison with the target branch.

    If target_branch is specified, finds merge-base with it.
    Otherwise attempts to find the nearest parent branch through heuristics:
    - origin/main, origin/master
    - upstream/main, upstream/master
    - main, master (local branches)

    Args:
        root: Repository root directory
        target_branch: Target branch for comparison (optional)

    Returns:
        Commit SHA of merge base, or None if not found
    """
    if target_branch:
        # Check if the specified branch exists
        refs = run_git(root, ["show-ref", "--verify", f"refs/heads/{target_branch}"])
        effective_branch = target_branch

        if not refs:
            # Try remote branch
            refs = run_git(root, ["show-ref", "--verify", f"refs/remotes/origin/{target_branch}"])
            if refs:
                effective_branch = f"origin/{target_branch}"

        if refs or target_branch.startswith(("origin/", "upstream/")):
            # Find merge-base with the specified branch
            merge_base = run_git(root, ["merge-base", "HEAD", effective_branch])
            return merge_base[0] if merge_base else effective_branch

    # Heuristic search for parent branch
    candidates = [
        "origin/main", "origin/master",
        "upstream/main", "upstream/master",
        "main", "master"
    ]

    for candidate in candidates:
        if candidate.startswith(("origin/", "upstream/")):
            refs = run_git(root, ["show-ref", "--verify", f"refs/remotes/{candidate}"])
        else:
            refs = run_git(root, ["show-ref", "--verify", f"refs/heads/{candidate}"])

        if refs:
            merge_base = run_git(root, ["merge-base", "HEAD", candidate])
            if merge_base:
                return merge_base[0]

    return None


def is_git_repo(path: Path) -> bool:
    """
    Check if path is inside a git repository.

    Handles both regular repositories (.git is a directory)
    and worktrees/submodules (.git is a file containing gitdir reference).

    Args:
        path: Path to check

    Returns:
        True if path is in a git repository
    """
    git_path = path / ".git"

    # Regular repository: .git is a directory
    if git_path.is_dir():
        return True

    # Worktree or submodule: .git is a file with "gitdir: <path>" content
    if git_path.is_file():
        try:
            content = git_path.read_text(encoding="utf-8").strip()
            return content.startswith("gitdir:")
        except Exception:
            return False

    return False


__all__ = [
    "run_git",
    "find_merge_base",
    "is_git_repo",
]
