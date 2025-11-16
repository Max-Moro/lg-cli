"""
Python function body optimization.
"""
from typing import Optional

from ..context import ProcessingContext
from ..optimizations import FunctionBodyOptimizer
from ..tree_sitter_support import Node


def remove_function_body_with_definition(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        func_def: Node,
        body_node: Node,
        func_type: str
) -> None:
    """
    Remove function bodies using function_definition.

    Args:
        root_optimizer: Universal function body optimizer
        context: Processing context with document access
        func_def: function_definition node
        body_node: Function body node
        func_type: Function type ("function" or "method")
    """
    # Find docstring in function body
    docstring_node = _find_docstring_in_body(body_node)

    if docstring_node is None:
        # No docstring - remove everything after ':'
        _remove_after_colon(root_optimizer, context, func_def, body_node, func_type)
    else:
        # Has docstring, use preservation logic
        _remove_function_body_preserve_docstring(root_optimizer, context, docstring_node, body_node, func_type)

def _remove_after_colon(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        func_def: Node,
        body_node: Node,
        func_type: str
) -> None:
    """Remove everything after ':' in function_definition."""
    # Find ':' that comes right after parameters node
    colon_node = _find_colon_after_parameters(func_def)

    if colon_node is None:
        # Fallback to standard logic
        return root_optimizer.remove_function_body(context, body_node, func_type)

    # Compute absolute position of ':' after parameters
    colon_end_char = context.doc.byte_to_char_position(colon_node.end_byte)

    # Remove everything from position after ':' to end of body
    body_start_char, body_end_char = context.doc.get_node_range(body_node)
    removal_start = colon_end_char  # After ':'
    removal_end = body_end_char

    # Determine proper indentation based on function type
    indent_prefix = _get_indent_prefix(func_type)

    # Use common helper with correct formatting
    return root_optimizer.apply_function_body_removal(
        context=context,
        start_char=removal_start,
        end_char=removal_end,
        func_type=func_type,
        placeholder_prefix=indent_prefix
    )

def _remove_function_body_preserve_docstring(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        docstring_node: Node,
        body_node: Node,
        func_type: str
) -> None:
    """
    Remove function/method body while preserving docstring if present.
    """
    # Has docstring - remove only the part after it
    body_start_char, body_end_char = context.doc.get_node_range(body_node)

    # Find position to start removal - right after docstring
    docstring_end_char = context.doc.byte_to_char_position(docstring_node.end_byte)

    # Check if there's code after docstring
    if docstring_end_char >= body_end_char:
        # No code after docstring - keep only docstring
        return None

    # Compute what to remove (from end of docstring to end of body)
    removal_start = docstring_end_char
    removal_end = body_end_char

    # Check if there's anything to remove
    removal_start_line = context.doc.get_line_number(removal_start)
    body_end_line = context.doc.get_line_range(body_node)[1]
    lines_removed = max(0, body_end_line - removal_start_line + 1)

    if lines_removed <= 0:
        # Nothing to remove after docstring
        return None

    # Determine proper indentation based on function type
    indent_prefix = _get_indent_prefix(func_type)

    # Use common helper with correct formatting
    return root_optimizer.apply_function_body_removal(
        context=context,
        start_char=removal_start,
        end_char=removal_end,
        func_type=func_type,
        placeholder_prefix=indent_prefix
    )


def _get_indent_prefix(func_type: str) -> str:
    """
    Determine proper indentation for placeholder based on function type.

    Args:
        func_type: Function type ("method" or "function")

    Returns:
        String with proper indentation for placeholder
    """
    if func_type == "method":
        return "\n        "  # Class method: 8 spaces
    else:
        return "\n    "      # Top-level function: 4 spaces


def _find_colon_after_parameters(func_def: Node) -> Optional[Node]:
    """
    Find ':' that comes right after parameters node in function_definition.
    """
    # Search for parameters node
    parameters_node = None
    for child in func_def.children:
        if child.type == "parameters":
            parameters_node = child
            break

    if parameters_node is None:
        return None

    # Search for ':' that comes right after parameters
    found_parameters = False
    for child in func_def.children:
        if child == parameters_node:
            found_parameters = True
            continue
        if found_parameters and child.type == ":":
            return child

    return None


def _find_docstring_in_body(body_node: Node) -> Optional[Node]:
    """
    Find docstring in function body (first expression_statement with string).
    """
    # Search for first statement in body
    for child in body_node.children:
        if child.type == "expression_statement":
            # Search for string inside expression_statement
            for expr_child in child.children:
                if expr_child.type == "string":
                    return child  # Return entire expression_statement
            # If first expression_statement doesn't contain string, it's not a docstring
            break

    return None