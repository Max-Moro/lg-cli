"""
Python code profiles for declarative element collection.

Describes all code element types in Python:
- Classes
- Functions (top-level)
- Methods (inside classes)
- Variables (module-level)

Python uses naming conventions for visibility:
- __name__ (dunder methods) = public
- __name (double underscore) = private
- _name (single underscore) = protected
- name = public
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Python element from node.
    """
    # Special handling for assignments
    if node.type == "assignment":
        # In assignment, the left side is the variable name
        for child in node.children:
            if child.type == "identifier":
                return doc.get_node_text(child)

    # Search for child node with function/class/method name
    for child in node.children:
        if child.type == "identifier":
            return doc.get_node_text(child)

    # For some node types, name may be in the name field
    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _is_public_python(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if Python element is public based on naming convention.

    Rules:
    - __name__ (dunder) = public
    - __name (double underscore) = private
    - _name (single underscore) = protected/private
    - name = public
    """
    name = _extract_name(node, doc)
    if not name:
        return True  # No name = public by default

    # Special Python methods (dunder methods) are considered public
    if name.startswith("__") and name.endswith("__"):
        return True

    # Names starting with two underscores are private (name mangling)
    if name.startswith("__"):
        return False

    # Names starting with one underscore are protected/private
    if name.startswith("_"):
        return False

    # All others are public
    return True


def _find_python_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find docstring at the start of function body.

    In Python, a docstring is the first expression statement that contains
    a string literal (not evaluated for side effects).
    """
    for child in body_node.children:
        if child.type == "expression_statement":
            for expr_child in child.children:
                if expr_child.type == "string":
                    return child  # Return expression_statement containing string
            # First expression_statement without string is not a docstring
            break
    return None


PYTHON_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="python",
    profiles=[
        ElementProfile(
            name="class",
            query="(class_definition) @element",
            is_public=_is_public_python,
        ),

        # Python has single node type (function_definition) for both.
        # Distinguish via is_inside_container check.
        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_python,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_definition"}
            ),
            has_body=True,
            docstring_extractor=_find_python_docstring,
        ),

        ElementProfile(
            name="method",
            query="(function_definition) @element",
            is_public=_is_public_python,
            additional_check=lambda node, doc: is_inside_container(
                node, {"class_definition"}
            ),
            has_body=True,
            docstring_extractor=_find_python_docstring,
        ),

        ElementProfile(
            name="variable",
            query="(assignment) @element",
            is_public=_is_public_python,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_definition"}
            ),
        ),
    ],

    decorator_types={"decorator"},
    comment_types={"comment"},
    name_extractor=_extract_name,
)


__all__ = ["PYTHON_CODE_DESCRIPTOR"]
