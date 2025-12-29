"""
GitIgnore service with correct recursive .gitignore semantics.

Implements proper Git behavior:
- All .gitignore files are treated uniformly (root is not special)
- Patterns are relative to their .gitignore location
- For a file check: collect .gitignore files from root to file's directory
- Combine patterns into single PathSpec — last match wins (supports !pattern)
- Lazy loading with caching for performance
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Dict, List

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

    Implements correct Git .gitignore semantics:
    - Each .gitignore applies to its directory and subdirectories
    - Patterns are relative to the .gitignore location
    - When checking a file, all .gitignore files from root to file's
      directory are collected and combined
    - Last matching pattern wins (supports negation with !pattern)

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

        # Cache of .gitignore patterns by directory path (relative to root)
        # Key: directory path relative to root ("" for root, "src", "src/utils", etc.)
        # Value: List of (pattern, is_negation) tuples, or None if no .gitignore
        self._gitignore_cache: Dict[str, Optional[List[str]]] = {}

        # Cache of check results
        self._result_cache: Dict[str, bool] = {}

    def _read_gitignore(self, gitignore_path: Path) -> List[str]:
        """
        Read and parse a .gitignore file.

        Args:
            gitignore_path: Absolute path to .gitignore file

        Returns:
            List of non-empty, non-comment patterns (preserving order)
        """
        try:
            content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
            patterns = []
            for line in content.splitlines():
                # Strip trailing whitespace but preserve leading (significant for patterns)
                line = line.rstrip()
                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue
                patterns.append(line)
            return patterns
        except Exception as e:
            logger.warning(f"Failed to read {gitignore_path}: {e}")
            return []

    def _get_gitignore_patterns(self, dir_rel: str) -> Optional[List[str]]:
        """
        Get .gitignore patterns for a directory (with caching).

        Args:
            dir_rel: Directory path relative to root ("" for root)

        Returns:
            List of patterns or None if no .gitignore in this directory
        """
        if dir_rel in self._gitignore_cache:
            return self._gitignore_cache[dir_rel]

        # Build absolute path to .gitignore
        if dir_rel:
            gitignore_path = self.root / dir_rel / ".gitignore"
        else:
            gitignore_path = self.root / ".gitignore"

        if gitignore_path.is_file():
            patterns = self._read_gitignore(gitignore_path)
            self._gitignore_cache[dir_rel] = patterns if patterns else None
        else:
            self._gitignore_cache[dir_rel] = None

        return self._gitignore_cache[dir_rel]

    def _collect_patterns_for_path(self, rel_path: str) -> List[str]:
        """
        Collect all applicable .gitignore patterns for a path.

        Walks from root to the file's parent directory, collecting patterns
        from each .gitignore file. Patterns are transformed to be relative
        to root by prepending the .gitignore directory path.

        Args:
            rel_path: File path relative to root (POSIX format)

        Returns:
            Combined list of patterns (order preserved for last-match-wins)
        """
        # Normalize path
        rel_path_clean = rel_path.strip("/")

        # Get parent directory parts
        parts = rel_path_clean.split("/")
        if len(parts) > 1:
            dir_parts = parts[:-1]
        else:
            dir_parts = []

        # Collect patterns from root to file's parent directory
        all_patterns: List[str] = []

        # Check root .gitignore
        root_patterns = self._get_gitignore_patterns("")
        if root_patterns:
            all_patterns.extend(root_patterns)

        # Check each parent directory's .gitignore
        current_dir = ""
        for part in dir_parts:
            if current_dir:
                current_dir = f"{current_dir}/{part}"
            else:
                current_dir = part

            dir_patterns = self._get_gitignore_patterns(current_dir)
            if dir_patterns:
                # Transform patterns to be relative to root
                for pattern in dir_patterns:
                    transformed = self._transform_pattern(pattern, current_dir)
                    all_patterns.append(transformed)

        return all_patterns

    def _transform_pattern(self, pattern: str, dir_rel: str) -> str:
        """
        Transform a pattern from .gitignore to be relative to root.

        Git .gitignore patterns are relative to the .gitignore location.
        We need to transform them to be relative to root for unified matching.

        Args:
            pattern: Original pattern from .gitignore
            dir_rel: Directory containing .gitignore (relative to root)

        Returns:
            Pattern transformed to be relative to root
        """
        # Handle negation patterns
        is_negation = pattern.startswith("!")
        if is_negation:
            pattern = pattern[1:]

        # Patterns starting with / are anchored to .gitignore directory
        if pattern.startswith("/"):
            # Remove leading / and prepend directory
            pattern = pattern[1:]
            if dir_rel:
                pattern = f"{dir_rel}/{pattern}"
        else:
            # Non-anchored patterns can match anywhere in subtree
            # Prepend **/ only if pattern doesn't already have path separators
            # at the beginning (to avoid matching above the .gitignore location)
            if dir_rel:
                if "/" in pattern and not pattern.startswith("**/"):
                    # Pattern with path component - anchor to directory
                    pattern = f"{dir_rel}/{pattern}"
                else:
                    # Simple pattern (like *.log) - match anywhere in subtree
                    pattern = f"{dir_rel}/**/{pattern}"
            else:
                # Root .gitignore - pattern stays as is for non-anchored
                if "/" not in pattern and not pattern.startswith("**/"):
                    pattern = f"**/{pattern}"

        # Restore negation
        if is_negation:
            pattern = f"!{pattern}"

        return pattern

    def is_ignored(self, rel_path: str) -> bool:
        """
        Check if a path is ignored by .gitignore rules.

        Implements correct Git semantics:
        - Collects all .gitignore files from root to file's directory
        - Combines patterns with last-match-wins semantics
        - Supports negation patterns (!pattern)

        Args:
            rel_path: Path relative to repository root (POSIX format)

        Returns:
            True if path is ignored
        """
        # Check cache first
        cache_key = rel_path.lower()
        if cache_key in self._result_cache:
            return self._result_cache[cache_key]

        # Collect all applicable patterns
        patterns = self._collect_patterns_for_path(rel_path)

        if not patterns:
            self._result_cache[cache_key] = False
            return False

        # Build PathSpec and check
        # pathspec with GitWildMatchPattern handles negation correctly
        # when patterns are in order (last match wins)
        try:
            spec = PathSpec.from_lines(GitWildMatchPattern, patterns)
            result = spec.match_file(rel_path.lower())
        except Exception as e:
            logger.warning(f"Failed to match patterns for {rel_path}: {e}")
            result = False

        self._result_cache[cache_key] = result
        return result

    def is_dir_ignored(self, rel_dir: str) -> bool:
        """
        Check if a directory is ignored.

        Args:
            rel_dir: Directory path relative to root (POSIX format)

        Returns:
            True if directory is ignored
        """
        # Check both with and without trailing slash
        rel_dir_clean = rel_dir.strip("/")
        return self.is_ignored(rel_dir_clean) or self.is_ignored(rel_dir_clean + "/")

    def should_descend(self, rel_dir: str) -> bool:
        """
        Check if we should descend into a directory during traversal.

        Args:
            rel_dir: Directory path relative to root (POSIX format)

        Returns:
            True if we should descend into the directory
        """
        return not self.is_dir_ignored(rel_dir)

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._gitignore_cache.clear()
        self._result_cache.clear()


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
