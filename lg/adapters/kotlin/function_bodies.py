"""
Kotlin function body optimization.
Handles KDoc preservation when stripping function bodies.
"""
from typing import Optional

from ..context import ProcessingContext
from ..optimizations import FunctionBodyOptimizer
from ..tree_sitter_support import Node


def remove_function_body_with_kdoc(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        func_def: Optional[Node],
        body_node: Node,
        func_type: str
) -> None:
    """
    Удаление тел функций Kotlin с сохранением KDoc.
    
    KDoc может находиться в двух местах:
    1. Перед функцией как предыдущий sibling (стандартный случай)
    2. Внутри тела функции как первый элемент (нестандартно, но возможно)
    
    Args:
        root_optimizer: Универсальный оптимизатор тел функций
        context: Контекст обработки с доступом к документу
        func_def: Узел function_declaration (может быть None для lambda)
        body_node: Узел тела функции
        func_type: Тип функции ("function" или "method")
    """
    # Для lambda нет KDoc, используем стандартную обработку
    if func_def is None or func_def.type != "function_declaration":
        return root_optimizer.remove_function_body(context, body_node, func_type)
    
    # 1. Проверяем KDoc перед функцией (стандартный случай)
    kdoc_before = _find_kdoc_before_function(func_def, context)
    
    if kdoc_before is not None:
        # KDoc находится снаружи, просто удаляем тело
        # KDoc будет сохранен автоматически
        return root_optimizer.remove_function_body(context, body_node, func_type)
    
    # 2. Проверяем KDoc внутри тела функции
    kdoc_inside = _find_kdoc_in_body(body_node, context)
    
    if kdoc_inside is None:
        # Нет KDoc вообще - удаляем тело стандартным образом
        return root_optimizer.remove_function_body(context, body_node, func_type)

    # KDoc внутри тела - удаляем только часть после него
    return _remove_function_body_preserve_kdoc(root_optimizer, context, kdoc_inside, body_node, func_type)


def _find_kdoc_before_function(func_node: Node, context: ProcessingContext) -> Optional[Node]:
    """
    Ищет KDoc комментарий непосредственно перед функцией.
    
    KDoc должен быть block_comment, начинающимся с /** и находящимся
    непосредственно перед function_declaration.
    
    Args:
        func_node: Узел function_declaration
        context: Контекст обработки
        
    Returns:
        Узел block_comment с KDoc или None
    """
    parent = func_node.parent
    if not parent:
        return None
    
    # Находим индекс текущей функции среди siblings
    siblings = parent.children
    func_index = None
    for i, sibling in enumerate(siblings):
        if sibling == func_node:
            func_index = i
            break
    
    if func_index is None or func_index == 0:
        return None
    
    # Проверяем предыдущий sibling
    prev_sibling = siblings[func_index - 1]
    
    if prev_sibling.type == "block_comment":
        # Проверяем, является ли это KDoc (начинается с /**)
        text = context.doc.get_node_text(prev_sibling)
        if text.startswith("/**"):
            return prev_sibling
    
    return None


def _find_kdoc_in_body(body_node: Node, context: ProcessingContext) -> Optional[Node]:
    """
    Ищет KDoc комментарий в начале тела функции.
    
    Args:
        body_node: Узел function_body
        context: Контекст обработки
        
    Returns:
        Узел block_comment с KDoc или None
    """
    # Тело функции в Kotlin - это function_body -> block -> statements
    # Ищем первый block внутри function_body
    block_node = None
    for child in body_node.children:
        if child.type == "block":
            block_node = child
            break
    
    if not block_node:
        return None
    
    # Ищем первый block_comment в block
    for child in block_node.children:
        # Пропускаем открывающую скобку {
        if child.type in ("{", "}"):
            continue
        
        # Если первый значимый узел - block_comment, проверяем его
        if child.type == "block_comment":
            text = context.doc.get_node_text(child)
            if text.startswith("/**"):
                return child
        
        # Если встретили что-то другое - KDoc должен быть первым
        break
    
    return None


def _remove_function_body_preserve_kdoc(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        kdoc_node: Node,
        body_node: Node,
        func_type: str
) -> None:
    """
    Удаляет тело функции, сохраняя KDoc внутри него.
    
    Args:
        root_optimizer: Универсальный оптимизатор тел функций
        context: Контекст обработки
        kdoc_node: Узел KDoc комментария
        body_node: Узел тела функции
        func_type: Тип функции
    """
    # Получаем диапазоны
    body_start_char, body_end_char = context.doc.get_node_range(body_node)
    kdoc_end_char = context.doc.byte_to_char_position(kdoc_node.end_byte)
    
    # Проверяем, есть ли код после KDoc
    if kdoc_end_char >= body_end_char:
        # Нет кода после KDoc - оставляем только KDoc и закрывающую скобку
        return None
    
    # Вычисляем что удаляем (от конца KDoc до конца тела)
    removal_start = kdoc_end_char
    removal_end = body_end_char
    
    # Проверяем, есть ли что удалять
    removal_start_line = context.doc.get_line_number(removal_start)
    body_end_line = context.doc.get_line_range(body_node)[1]
    lines_removed = max(0, body_end_line - removal_start_line + 1)
    
    if lines_removed <= 0:
        # Нечего удалять после KDoc
        return None
    
    # Определяем правильный отступ на основе типа функции
    indent_prefix = _get_indent_prefix(func_type)
    
    # Используем общий helper с правильным форматированием
    return root_optimizer.apply_function_body_removal(
        context=context,
        start_char=removal_start,
        end_char=removal_end,
        func_type=func_type,
        placeholder_prefix=indent_prefix
    )


def _get_indent_prefix(func_type: str) -> str:
    """
    Определяет правильный отступ для плейсхолдера на основе типа функции.
    
    Args:
        func_type: Тип функции ("method" или "function")
        
    Returns:
        Строка с правильным отступом для плейсхолдера
    """
    if func_type == "method":
        return "\n        "  # Метод класса: 8 пробелов
    else:
        return "\n    "      # Функция верхнего уровня: 4 пробела

