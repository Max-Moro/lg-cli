"""
Utilities for creating files and directories in tests.

Unifies all file-related functions that were duplicated
in various conftest.py files.
"""

from __future__ import annotations

from pathlib import Path


def write(p: Path, text: str) -> Path:
    """
    Writes text to a file, creating parent directories as needed.

    Base function for all file operations. Replaces duplicated write()
    functions from various conftest.py files.

    Args:
        p: Path to the file
        text: Content to write

    Returns:
        Path to the created file
    """
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def write_source_file(p: Path, content: str, language: str = "python") -> Path:
    """
    Creates a source file with content for a specific language.

    Adds a comment with the file name and processes the content.

    Args:
        p: Path to the file
        content: File content
        language: Programming language for correct comment syntax

    Returns:
        Path to the created file
    """
    comment_map = {
        "python": "# ",
        "typescript": "// ",
        "javascript": "// ",
        "java": "// ",
        "cpp": "// ",
        "c": "// ",
        "scala": "// "
    }

    comment_prefix = comment_map.get(language, "# ")

    lines = [f"{comment_prefix}Source file: {p.name}", ""]

    if content:
        lines.append(content.strip())

    return write(p, "\n".join(lines) + "\n")


def write_markdown(p: Path, title: str = "", content: str = "", h1_prefix: str = "# ") -> Path:
    """
    Creates a Markdown file with a title and content.

    Args:
        p: Path to the file
        title: Title (if set, added as H1)
        content: Main content
        h1_prefix: Prefix for H1 title (allows creating files without H1)

    Returns:
        Path to the created file
    """
    lines = []

    if title:
        lines.append(f"{h1_prefix}{title}")
        lines.append("")  # empty line after title

    if content:
        lines.append(content.strip())

    return write(p, "\n".join(lines) + "\n")


def write_context(
    root: Path,
    name: str,
    content: str,
    include_meta_sections: list[str] | None = None
) -> Path:
    """
    Creates a context file (.ctx.md) with automatic frontmatter.

    Automatically adds ai-interaction meta-section and frontmatter for contexts
    that need integration mode-set support.

    Args:
        root: Project root (NOT lg-cfg directory)
        name: Context name (without .ctx.md suffix)
        content: Context content (without frontmatter)
        include_meta_sections: Meta-sections to include. Default: ["ai-interaction"].
                               Pass empty list [] to disable frontmatter.

    Returns:
        Path to the created context file
    """
    # Default: include ai-interaction
    if include_meta_sections is None:
        include_meta_sections = ["ai-interaction"]

    # Build frontmatter if needed
    final_content = content
    if include_meta_sections:
        # Create ai-interaction meta-section if needed
        if "ai-interaction" in include_meta_sections:
            from .config_builders import create_integration_mode_section
            create_integration_mode_section(root)

        # Add frontmatter
        include_yaml = ", ".join(f'"{s}"' for s in include_meta_sections)
        frontmatter = f"---\ninclude: [{include_yaml}]\n---\n"
        final_content = frontmatter + content

    return write(root / "lg-cfg" / f"{name}.ctx.md", final_content)


__all__ = [
    "write", "write_source_file", "write_markdown", "write_context"
]