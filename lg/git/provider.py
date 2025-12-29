"""
Git VCS provider implementation.

Provides GitVcs class that implements VcsProvider protocol
for collecting information about changed files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Set, Optional

from . import VcsProvider
from .utils import run_git, find_merge_base


class GitVcs(VcsProvider):
    """
    Git VCS provider.

    Collects changed files:
    - git diff --name-only (unstaged)
    - git diff --name-only --cached (staged)
    - git ls-files --others --exclude-standard (untracked)
    """

    def changed_files(self, root: Path) -> Set[str]:
        """
        Return files changed in the working tree.

        Includes:
        - Unstaged changes
        - Staged changes
        - Untracked files (not ignored)

        Args:
            root: Repository root directory

        Returns:
            Set of relative POSIX paths
        """
        files: Set[str] = set()
        files.update(run_git(root, ["diff", "--name-only"]))
        files.update(run_git(root, ["diff", "--name-only", "--cached"]))
        files.update(run_git(root, ["ls-files", "--others", "--exclude-standard"]))

        # Normalize to POSIX paths
        return {Path(p).as_posix() for p in files}

    def branch_changed_files(self, root: Path, target_branch: Optional[str] = None) -> Set[str]:
        """
        Return files changed in the current branch relative to target branch.

        Args:
            root: Repository root directory
            target_branch: Target branch for comparison (auto-detected if None)

        Returns:
            Set of relative POSIX paths changed in the branch
        """
        base_ref = find_merge_base(root, target_branch)
        if not base_ref:
            # Fallback to regular changes if we cannot find base
            return self.changed_files(root)

        files: Set[str] = set()

        # Files changed between the base point and HEAD
        files.update(run_git(root, ["diff", "--name-only", f"{base_ref}..HEAD"]))

        # Also add current working changes
        files.update(run_git(root, ["diff", "--name-only"]))
        files.update(run_git(root, ["diff", "--name-only", "--cached"]))
        files.update(run_git(root, ["ls-files", "--others", "--exclude-standard"]))

        # Normalize to POSIX paths
        return {Path(p).as_posix() for p in files}


__all__ = ["GitVcs"]
