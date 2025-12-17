from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommentStyle:
    """Comment style description for a language."""

    single_line: str
    """Single-line comment marker (e.g., '//' or '#')."""

    multi_line: tuple[str, str]
    """Multi-line comment markers (e.g., ('/*', '*/'))."""

    doc_markers: tuple[str, str]
    """Documentation comment markers (e.g., ('/**', '*/') or ('///', ''))."""
