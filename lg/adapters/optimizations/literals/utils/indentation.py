"""Утилиты для определения отступов в литералах."""

from __future__ import annotations


def detect_base_indent(text: str, byte_pos: int) -> str:
    """
    Determine indentation of the line containing the literal.

    Extracts the whitespace characters (spaces and tabs) from the beginning
    of the line up to the position where the literal starts.

    Args:
        text: Full source text
        byte_pos: Byte position where literal starts

    Returns:
        Indentation string (spaces/tabs)

    Example:
        >>> text = "def foo():\\n    x = [1, 2, 3]"
        >>> pos = text.find('[')
        >>> detect_base_indent(text, pos)
        '    '
    """
    line_start = text.rfind('\n', 0, byte_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1

    indent = ""
    for i in range(line_start, min(byte_pos, len(text))):
        if text[i] in ' \t':
            indent += text[i]
        else:
            break

    return indent


def detect_element_indent(literal_text: str, base_indent: str) -> str:
    """
    Determine indentation for elements inside a multiline literal.

    Scans the literal's content to find the indentation level used for
    its elements. If the literal is single-line or indentation cannot
    be determined, returns base_indent + 4 spaces.

    Args:
        literal_text: Full literal text (including delimiters)
        base_indent: Base indentation of the line containing the literal

    Returns:
        Element indentation string

    Example:
        >>> literal = "[\\n    1,\\n    2\\n]"
        >>> detect_element_indent(literal, "")
        '    '
    """
    lines = literal_text.split('\n')
    if len(lines) < 2:
        return base_indent + "    "

    for line in lines[1:]:
        stripped = line.strip()
        if stripped and not stripped.startswith((']', '}', ')')):
            indent = ""
            for char in line:
                if char in ' \t':
                    indent += char
                else:
                    break
            if indent:
                return indent

    return base_indent + "    "
