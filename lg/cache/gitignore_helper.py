"""
Utility for managing the root .gitignore file.

Provides centralized logic for adding entries to .gitignore
for various caching system components.
"""

from __future__ import annotations

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

__all__ = ["ensure_gitignore_entry"]


def ensure_gitignore_entry(root: Path, entry: str, *, comment: str | None = None) -> bool:
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
        # Normalize entry (remove extra whitespace, ensure trailing slash for directories)
        entry_normalized = entry.strip()
        if not entry_normalized:
            logger.warning("Empty gitignore entry requested, skipping")
            return False

        # Read existing file if it exists
        existing_lines = []
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text(encoding="utf-8")
                existing_lines = content.splitlines()
            except Exception as e:
                logger.warning(f"Failed to read .gitignore: {e}")
                # Continue with empty list

        # Check for existing entry (ignore comments and empty lines)
        for line in existing_lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith("#"):
                if line_stripped == entry_normalized:
                    # Entry already exists
                    return False

        # Build new entry with optional comment
        new_content_parts = []

        # Preserve existing content
        if existing_lines:
            new_content_parts.append("\n".join(existing_lines))
            # Add blank line before our entry if file is not empty
            # and last line is not empty
            if existing_lines[-1].strip():
                new_content_parts.append("")

        # Add comment if provided
        if comment:
            new_content_parts.append(f"# {comment}")

        # Add the entry itself
        new_content_parts.append(entry_normalized)

        # Write updated .gitignore
        final_content = "\n".join(new_content_parts)
        if not final_content.endswith("\n"):
            final_content += "\n"

        gitignore_path.write_text(final_content, encoding="utf-8")

        logger.info(f"Added '{entry_normalized}' to .gitignore")
        return True

    except Exception as e:
        # Best-effort: log error but do not break the program
        logger.warning(f"Failed to update .gitignore: {e}")
        return False
