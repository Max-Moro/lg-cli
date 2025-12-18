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


# Shared comment style constants for common language families

# C-family languages: C, C++, Java, JavaScript, TypeScript, Scala, Kotlin
C_STYLE_COMMENTS = CommentStyle(
    single_line="//",
    multi_line=("/*", "*/"),
    doc_markers=("/**", "*/")
)

# Hash-style comments: Python, Ruby, Shell
HASH_STYLE_COMMENTS = CommentStyle(
    single_line="#",
    multi_line=('"""', '"""'),
    doc_markers=('"""', '"""')
)

# Go uses // for doc comments (no special marker like /** */)
GO_STYLE_COMMENTS = CommentStyle(
    single_line="//",
    multi_line=("/*", "*/"),
    doc_markers=("//", "")
)

# Rust uses /// for outer doc and //! for inner doc comments
RUST_STYLE_COMMENTS = CommentStyle(
    single_line="//",
    multi_line=("/*", "*/"),
    doc_markers=("///", "")
)
