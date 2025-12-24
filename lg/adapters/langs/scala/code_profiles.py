"""
Scala code profiles for declarative element collection.

Describes all code element types in Scala:
- Classes (regular)
- Case classes
- Traits
- Objects (singletons)
- Functions (top-level)
- Methods (inside classes/traits/objects)
- Variables/Properties (val/var at various levels)
- Fields (class members)

Scala uses explicit visibility modifiers for public API determination:
- private = private
- protected = protected (treated as private for public API)
- internal = module-level (treated as private for public API)
- No modifier = public (default)
"""

from __future__ import annotations

from typing import Optional

from ...shared import ElementProfile, LanguageCodeDescriptor, is_inside_container
from ...tree_sitter_support import Node, TreeSitterDocument


def _is_case_class(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Check if a class definition is a case class.

    Case classes have 'case' modifier in Scala.
    """
    node_text = doc.get_node_text(node)
    return "case class" in node_text[:50]


def _extract_name(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract name of Scala element from node.
    """
    # For val/var definitions, name is in pattern field
    if node.type in ("val_definition", "var_definition", "val_declaration", "var_declaration"):
        pattern_node = node.child_by_field_name("pattern")
        if pattern_node and pattern_node.type == "identifier":
            return doc.get_node_text(pattern_node)

    for child in node.children:
        if child.type == "identifier":
            return doc.get_node_text(child)

    name_node = node.child_by_field_name("name")
    if name_node:
        return doc.get_node_text(name_node)

    return None


def _get_visibility_modifier(node: Node, doc: TreeSitterDocument) -> Optional[str]:
    """
    Extract visibility modifier from Scala node.

    Scala visibility modifiers: private, protected, public.
    No modifier means public (default).
    """
    for child in node.children:
        if child.type == "modifiers":
            for modifier_child in child.children:
                if modifier_child.type == "access_modifier":
                    return doc.get_node_text(modifier_child).strip()
    return None


def _is_public_scala(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Determine if Scala element is public based on visibility modifiers.

    Scala rules:
    - private = private
    - protected = protected (treated as private for public API)
    - No modifier = public (default)
    """
    modifier = _get_visibility_modifier(node, doc)

    if modifier in ("private", "protected"):
        return False

    return True


def _find_scala_docstring(body_node: Node, doc: TreeSitterDocument) -> Optional[Node]:
    """
    Find ScalaDoc at the start of Scala function body.

    In Scala, ScalaDoc is documentation that appears at the start of the body.
    It's a block_comment or multiline_comment starting with /** and should be preserved.
    """
    # Handle function_body wrapper - get actual block inside
    actual_body = body_node
    if body_node.type == "function_body":
        if body_node.children:
            actual_body = body_node.children[0]

    if actual_body.type != "block":
        return None

    for child in actual_body.children:
        if doc.get_node_text(child) == "{":
            continue

        if child.type in ("multiline_comment", "block_comment"):
            comment_text = doc.get_node_text(child)
            if comment_text.startswith("/**"):
                return child

        if child.type not in ("multiline_comment", "block_comment", "line_comment"):
            break

    return None


SCALA_CODE_DESCRIPTOR = LanguageCodeDescriptor(
    language="scala",
    profiles=[
        ElementProfile(
            name="class",
            query="(class_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not _is_case_class(node, doc),
        ),

        ElementProfile(
            name="case_class",
            query="(class_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: _is_case_class(node, doc),
        ),

        ElementProfile(
            name="trait",
            query="(trait_definition) @element",
            is_public=_is_public_scala,
        ),

        ElementProfile(
            name="object",
            query="(object_definition) @element",
            is_public=_is_public_scala,
        ),

        ElementProfile(
            name="type",
            query="(type_definition) @element",
            is_public=_is_public_scala,
        ),

        ElementProfile(
            name="function",
            query="(function_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
            has_body=True,
            docstring_extractor=_find_scala_docstring,
        ),

        ElementProfile(
            name="method",
            query="(function_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
            has_body=True,
            docstring_extractor=_find_scala_docstring,
        ),

        ElementProfile(
            name="function",
            query="(function_declaration) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
        ),

        ElementProfile(
            name="method",
            query="(function_declaration) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
        ),

        ElementProfile(
            name="variable",
            query="(val_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
        ),

        ElementProfile(
            name="variable",
            query="(var_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: not is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
        ),

        ElementProfile(
            name="field",
            query="(val_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
        ),

        ElementProfile(
            name="field",
            query="(var_definition) @element",
            is_public=_is_public_scala,
            additional_check=lambda node, doc: is_inside_container(
                node, {"class_definition", "object_definition", "trait_definition", "template_body"}
            ),
        ),
    ],

    decorator_types={"annotation"},
    comment_types={"comment", "block_comment", "multiline_comment"},
    name_extractor=_extract_name,
)


__all__ = ["SCALA_CODE_DESCRIPTOR"]
