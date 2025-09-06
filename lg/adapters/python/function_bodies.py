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
        func_type: str,
        placeholder_style: str
) -> None:
    """
    Удаление тел функций с использованием function_definition.

    Args:
        root_optimizer: Универсальный оптимизатор тел функций
        context: Контекст обработки с доступом к документу
        func_def: Узел function_definition
        body_node: Узел тела функции
        func_type: Тип функции ("function" или "method")
        placeholder_style: Стиль плейсхолдера
    """
    # Ищем docstring в теле функции
    docstring_node = _find_docstring_in_body(body_node)

    if docstring_node is None:
        # Нет docstring - удаляем всё после ':'
        _remove_after_colon(root_optimizer, context, func_def, body_node, func_type, placeholder_style)
    else:
        # Есть docstring, используем логику с preservation
        _remove_function_body_preserve_docstring(root_optimizer, context, docstring_node, body_node, func_type, placeholder_style)

def _remove_after_colon(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        func_def: Node,
        body_node: Node,
        func_type: str,
        placeholder_style: str
) -> None:
    """Удаление всего после ':' в function_definition."""
    # Найдем позицию ':' в function_definition
    func_text = context.doc.get_node_text(func_def)
    colon_pos = func_text.find(':')

    if colon_pos == -1:
        # Fallback к стандартной логике
        return root_optimizer.remove_function_body(context, body_node, func_type, placeholder_style)

    # Вычисляем абсолютную позицию ':'
    func_start = func_def.start_byte
    absolute_colon_pos = func_start + colon_pos

    # Удаляем всё от позиции после ':' до конца body
    body_start_byte, body_end_byte = context.doc.get_node_range(body_node)
    removal_start = absolute_colon_pos + 1  # После ':'
    removal_end = body_end_byte

    # Используем общий helper
    return root_optimizer.apply_function_body_removal(
        context=context,
        start_byte=removal_start,
        end_byte=removal_end,
        func_type=func_type,
        placeholder_style=placeholder_style,
        replacement_type=f"{func_type}_body_removal_simple",
        placeholder_prefix="\n    "
    )

def _remove_function_body_preserve_docstring(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        docstring_node: Node,
        body_node: Node,
        func_type: str,
        placeholder_style: str
) -> None:
    """
    Удаляет тело функции/метода, сохраняя docstring, если он есть.
    """
    # Есть docstring - удаляем только часть после него
    body_start_byte, body_end_byte = context.doc.get_node_range(body_node)

    # Найдём первый символ после docstring (обычно перевод строки)
    # Нужно найти следующий statement после docstring
    next_statement_start = _find_next_statement_after_docstring(body_node, docstring_node)

    if next_statement_start is None or next_statement_start >= body_end_byte:
        # Нет кода после docstring - оставляем только docstring
        return None

    # Вычисляем что удаляем (от начала следующего statement до конца тела)
    removal_start = next_statement_start
    removal_end = body_end_byte

    # Проверяем, есть ли что удалять
    removal_start_line = context.doc.get_line_number_for_byte(removal_start)
    body_end_line = context.doc.get_line_range(body_node)[1]
    lines_removed = max(0, body_end_line - removal_start_line + 1)

    if lines_removed <= 0:
        # Нечего удалять после docstring
        return None

    # Используем общий helper
    return root_optimizer.apply_function_body_removal(
        context=context,
        start_byte=removal_start,
        end_byte=removal_end,
        func_type=func_type,
        placeholder_style=placeholder_style,
        replacement_type=f"{func_type}_body_removal_preserve_docstring",
        placeholder_prefix="\n    "
    )


def _find_next_statement_after_docstring(body_node: Node, docstring_node: Node) -> Optional[int]:
    """
    Находит начальный байт следующего statement после docstring.
    """
    docstring_found = False
    for child in body_node.children:
        if docstring_found:
            # Нашли следующий statement после docstring
            return child.start_byte
        if child == docstring_node:
            docstring_found = True

    return None


def _find_docstring_in_body(body_node: Node) -> Optional[Node]:
    """
    Находит docstring в теле функции (первый expression_statement со string).
    """
    # Ищем первый statement в теле
    for child in body_node.children:
        if child.type == "expression_statement":
            # Ищем string внутри expression_statement
            for expr_child in child.children:
                if expr_child.type == "string":
                    return child  # Возвращаем весь expression_statement
            # Если первый expression_statement не содержит string, это не docstring
            break

    return None