from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Set, Optional

from . import VcsProvider


def _git(root: Path, args: list[str]) -> list[str]:
    try:
        out = subprocess.check_output(["git", "-C", str(root), *args], text=True, encoding="utf-8", errors="ignore")
        return [ln.strip() for ln in out.splitlines() if ln.strip()]
    except Exception:
        return []


def _find_merge_base_or_parent(root: Path, target_branch: Optional[str]) -> Optional[str]:
    """
    Find the base point for comparison with the target branch.

    If target_branch is specified, finds merge-base with it.
    Otherwise attempts to find the nearest parent branch through various heuristics:
    - origin/main, origin/master
    - upstream/main, upstream/master
    - main, master (local branches)
    """
    if target_branch:
        # Check if the specified branch exists
        refs = _git(root, ["show-ref", "--verify", f"refs/heads/{target_branch}"])
        if not refs:
            # Try remote branch
            refs = _git(root, ["show-ref", "--verify", f"refs/remotes/origin/{target_branch}"])
            if refs:
                target_branch = f"origin/{target_branch}"

        if refs or target_branch.startswith(("origin/", "upstream/")):
            # Find merge-base with the specified branch
            merge_base = _git(root, ["merge-base", "HEAD", target_branch])
            return merge_base[0] if merge_base else target_branch

    # Heuristic search for parent branch
    candidates = [
        "origin/main", "origin/master",
        "upstream/main", "upstream/master",
        "main", "master"
    ]

    for candidate in candidates:
        refs = _git(root, ["show-ref", "--verify", f"refs/remotes/{candidate}"])
        if not refs and not candidate.startswith(("origin/", "upstream/")):
            refs = _git(root, ["show-ref", "--verify", f"refs/heads/{candidate}"])

        if refs:
            merge_base = _git(root, ["merge-base", "HEAD", candidate])
            if merge_base:
                return merge_base[0]

    return None


class GitVcs(VcsProvider):
    """
    Collection of changed files:
      - git diff --name-only (unstaged)
      - git diff --name-only --cached (staged)
      - git ls-files --others --exclude-standard (untracked)
    """
    def changed_files(self, root: Path) -> Set[str]:
        s: Set[str] = set()
        s.update(_git(root, ["diff", "--name-only"]))
        s.update(_git(root, ["diff", "--name-only", "--cached"]))
        s.update(_git(root, ["ls-files", "--others", "--exclude-standard"]))
        # Convert to POSIX
        return {str(Path(p).as_posix()) for p in s}
    
    def branch_changed_files(self, root: Path, target_branch: Optional[str] = None) -> Set[str]:
        """
        Return files changed in the current branch relative to the target branch.

        Args:
            root: Git repository root
            target_branch: Target branch for comparison (if None, auto-detected)

        Returns:
            Set of POSIX paths of files changed in the current branch
        """
        base_ref = _find_merge_base_or_parent(root, target_branch)
        if not base_ref:
            # Fallback to regular changes if we cannot find base
            return self.changed_files(root)

        s: Set[str] = set()
        # Files changed between the base point and HEAD
        s.update(_git(root, ["diff", "--name-only", f"{base_ref}..HEAD"]))
        # Also add current working changes
        s.update(_git(root, ["diff", "--name-only"]))
        s.update(_git(root, ["diff", "--name-only", "--cached"]))
        s.update(_git(root, ["ls-files", "--others", "--exclude-standard"]))

        # Convert to POSIX
        return {str(Path(p).as_posix()) for p in s}
