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
    """Block documentation comment markers (e.g., ('/**', '*/') or ('\"\"\"', '\"\"\"'))."""

    line_doc_markers: tuple[str, ...] = ()
    """Line-based documentation comment markers (e.g., ('///',) or ('///', '//!'))."""


# Shared comment style constants for common language families

# C-family languages: C, C++, Java, JavaScript, TypeScript, Scala, Kotlin
C_STYLE_COMMENTS = CommentStyle(
    single_line="//",
    multi_line=("/*", "*/"),
    doc_markers=("/**", "*/"),
    line_doc_markers=("///",)
)

# Hash-style comments: Python, Ruby, Shell
HASH_STYLE_COMMENTS = CommentStyle(
    single_line="#",
    multi_line=('"""', '"""'),
    doc_markers=('"""', '"""'),
    line_doc_markers=()
)

# Go uses // for doc comments (no special marker like /** */)
GO_STYLE_COMMENTS = CommentStyle(
    single_line="//",
    multi_line=("/*", "*/"),
    doc_markers=("//", ""),
    line_doc_markers=()
)

# Rust uses /// for outer doc and //! for inner doc comments
# doc_markers is set to ("///", "") for placeholder generation (line-based style)
# line_doc_markers covers all Rust doc comment variants for is_documentation_comment()
RUST_STYLE_COMMENTS = CommentStyle(
    single_line="//",
    multi_line=("/*", "*/"),
    doc_markers=("///", ""),
    line_doc_markers=("///", "//!", "/**", "/*!",)
)
