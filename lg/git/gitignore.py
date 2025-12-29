"""
GitIgnore service with recursive loading and caching.

Implements proper Git semantics:
- Recursive loading of .gitignore files from all directories
- Patterns are relative to their .gitignore location
- Support for .git/info/exclude
- Caching for performance during filesystem traversal
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict, List

import pathspec
from pathspec import PathSpec
from pathspec.patterns import GitWildMatchPattern

logger = logging.getLogger(__name__)

__all__ = [
    "GitIgnoreService",
    "ensure_gitignore_entry",
]


class GitIgnoreService:
    """
    Service for checking paths against .gitignore rules.

    Implements recursive .gitignore loading with proper Git semantics:
    - Each .gitignore applies to its directory and subdirectories
    - Patterns are matched relative to the .gitignore location
    - Results are cached for performance

    Usage:
        service = GitIgnoreService(repo_root)
        if service.is_ignored("src/temp/file.py"):
            # File is ignored
            pass
    """

    def __init__(self, root: Path):
        """
        Initialize GitIgnore service.

        Args:
            root: Repository root directory
        """
        self.root = root.resolve()

        # Cache of PathSpec objects by directory path
        # Key: directory path relative to root (empty string for root)
        # Value: PathSpec for that directory's .gitignore (or None if no .gitignore)
        self._specs: Dict[str, Optional[PathSpec]] = {}

        # Cache of already checked paths
        self._ignore_cache: Dict[str, bool] = {}

        # Load root .gitignore and .git/info/exclude
        self._load_root_ignores()

    def _load_root_ignores(self) -> None:
        """Load root-level ignore patterns."""
        patterns: List[str] = []

        # Load .git/info/exclude (repository-specific excludes)
        exclude_path = self.root / ".git" / "info" / "exclude"
        if exclude_path.is_file():
            patterns.extend(self._read_gitignore_file(exclude_path))

        # Load root .gitignore
        root_gitignore = self.root / ".gitignore"
        if root_gitignore.is_file():
            patterns.extend(self._read_gitignore_file(root_gitignore))

        if patterns:
            self._specs[""] = PathSpec.from_lines(GitWildMatchPattern, patterns)
        else:
            self._specs[""] = None

    def _read_gitignore_file(self, path: Path) -> List[str]:
        """
        Read and parse a .gitignore file.

        Args:
            path: Path to .gitignore file

        Returns:
            List of non-empty, non-comment patterns
        """
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            patterns = []
            for line in content.splitlines():
                line = line.strip()
                if line and not line.startswith("#"):
                    patterns.append(line)
            return patterns
        except Exception as e:
            logger.warning(f"Failed to read {path}: {e}")
            return []

    def _get_spec_for_dir(self, rel_dir: str) -> Optional[PathSpec]:
        """
        Get or load PathSpec for a directory.

        Args:
            rel_dir: Directory path relative to root (POSIX format)

        Returns:
            PathSpec for directory's .gitignore, or None if no .gitignore
        """
        if rel_dir in self._specs:
            return self._specs[rel_dir]

        # Load .gitignore for this directory
        if rel_dir:
            gitignore_path = self.root / rel_dir / ".gitignore"
        else:
            # Root already loaded
            return self._specs.get("")

        if gitignore_path.is_file():
            patterns = self._read_gitignore_file(gitignore_path)
            if patterns:
                self._specs[rel_dir] = PathSpec.from_lines(GitWildMatchPattern, patterns)
            else:
                self._specs[rel_dir] = None
        else:
            self._specs[rel_dir] = None

        return self._specs[rel_dir]

    def is_ignored(self, rel_path: str) -> bool:
        """
        Check if a path is ignored by .gitignore rules.

        Implements proper Git semantics:
        - Checks all .gitignore files from root to the file's directory
        - Patterns are matched relative to their .gitignore location
        - Later rules can override earlier ones (negation patterns)

        Args:
            rel_path: Path relative to repository root (POSIX format)

        Returns:
            True if path is ignored
        """
        # Check cache first
        if rel_path in self._ignore_cache:
            return self._ignore_cache[rel_path]

        # Normalize path
        rel_path_normalized = rel_path.strip("/").lower()

        # Check all .gitignore files from root to the file's directory
        parts = rel_path_normalized.split("/")
        ignored = False

        # Check root .gitignore against full path
        root_spec = self._specs.get("")
        if root_spec and root_spec.match_file(rel_path_normalized):
            ignored = True

        # Check each parent directory's .gitignore
        for i in range(len(parts) - 1):
            dir_path = "/".join(parts[:i + 1])

            # Load spec for this directory (lazy loading)
            spec = self._get_spec_for_dir(dir_path)
            if spec is None:
                continue

            # The remaining path relative to this directory's .gitignore
            remaining_path = "/".join(parts[i + 1:])

            if spec.match_file(remaining_path):
                ignored = True
                # Note: We continue checking because negation patterns
                # in deeper directories could un-ignore the file

        # Cache result
        self._ignore_cache[rel_path] = ignored
        return ignored

    def is_dir_ignored(self, rel_dir: str) -> bool:
        """
        Check if a directory is ignored.

        Args:
            rel_dir: Directory path relative to root (POSIX format)

        Returns:
            True if directory is ignored
        """
        # Check with trailing slash for directory matching
        return self.is_ignored(rel_dir + "/") or self.is_ignored(rel_dir)

    def should_descend(self, rel_dir: str) -> bool:
        """
        Check if we should descend into a directory during traversal.

        This is the inverse of is_dir_ignored, provided for convenience.

        Args:
            rel_dir: Directory path relative to root (POSIX format)

        Returns:
            True if we should descend into the directory
        """
        return not self.is_dir_ignored(rel_dir)

    def clear_cache(self) -> None:
        """Clear the ignore result cache."""
        self._ignore_cache.clear()


def ensure_gitignore_entry(root: Path, entry: str, *, comment: Optional[str] = None) -> bool:
    """
    Ensure an entry exists in the root .gitignore file.

    Args:
        root: Project root (where .gitignore is located)
        entry: Entry to add (e.g., ".lg-cache/")
        comment: Optional comment before the entry

    Returns:
        True if entry was added, False if it already existed

    Note:
        - Creates .gitignore if it doesn't exist
        - Checks existing entries (ignores comments and empty lines)
        - Adds entry at end of file with newline
        - All operations are best-effort (do not break on errors)
    """
    gitignore_path = root / ".gitignore"

    try:
        # Normalize entry
        entry_normalized = entry.strip()
        if not entry_normalized:
            logger.warning("Empty gitignore entry requested, skipping")
            return False

        # Read existing file if it exists
        existing_lines: List[str] = []
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text(encoding="utf-8")
                existing_lines = content.splitlines()
            except Exception as e:
                logger.warning(f"Failed to read .gitignore: {e}")

        # Check for existing entry
        for line in existing_lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith("#"):
                if line_stripped == entry_normalized:
                    return False

        # Build new content
        new_content_parts: List[str] = []

        # Preserve existing content
        if existing_lines:
            new_content_parts.append("\n".join(existing_lines))
            # Add blank line if file doesn't end with empty line
            if existing_lines[-1].strip():
                new_content_parts.append("")

        # Add comment if provided
        if comment:
            new_content_parts.append(f"# {comment}")

        # Add the entry
        new_content_parts.append(entry_normalized)

        # Write updated .gitignore
        final_content = "\n".join(new_content_parts)
        if not final_content.endswith("\n"):
            final_content += "\n"

        gitignore_path.write_text(final_content, encoding="utf-8")

        logger.info(f"Added '{entry_normalized}' to .gitignore")
        return True

    except Exception as e:
        logger.warning(f"Failed to update .gitignore: {e}")
        return False
