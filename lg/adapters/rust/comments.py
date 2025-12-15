"""
Rust comment optimization.
"""


def is_documentation_comment(comment_text: str) -> bool:
    """
    Check if comment is Rust documentation.

    Rust documentation comments have specific markers:
    - /// - outer doc comment (single line)
    - //! - inner doc comment (single line)
    - /** ... */ - outer doc comment (multi-line)
    - /*! ... */ - inner doc comment (multi-line)

    Args:
        comment_text: The comment text to check

    Returns:
        True if this is a Rust documentation comment
    """
    stripped = comment_text.strip()
    # Check for all Rust documentation comment forms
    return (stripped.startswith('///') or
            stripped.startswith('//!') or
            stripped.startswith('/**') or
            stripped.startswith('/*!'))
