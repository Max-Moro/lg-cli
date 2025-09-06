"""
Python function body optimization.
"""
from typing import Optional

from ..context import ProcessingContext
from ..optimizations import FunctionBodyOptimizer
from ..tree_sitter_support import Node, TreeSitterDocument


def remove_function_body_with_definition(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        func_def: Node,
        body_node: Node,
        func_type: str,
        placeholder_style: str
) -> None:
    """
    Упрощенная версия удаления тел функций с использованием function_definition.
    
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
        # Нет docstring - удаляем всё после ':' (используем упрощенную логику)
        _remove_after_colon(context, func_def, body_node, func_type, placeholder_style)
    else:
        # Есть docstring - используем старую логику с preservation
        remove_function_body_preserve_docstring(
            root_optimizer=root_optimizer,
            context=context,
            body_node=body_node,
            func_type=func_type,
            placeholder_style=placeholder_style
        )


def _remove_after_colon(
        context: ProcessingContext,
        func_def: Node,
        body_node: Node,
        func_type: str,
        placeholder_style: str
) -> None:
    """Упрощенная функция удаления всего после ':' в function_definition."""
    # Найдем позицию ':' в function_definition
    func_text = context.doc.get_node_text(func_def)
    colon_pos = func_text.find(':')
    
    if colon_pos == -1:
        # Fallback к стандартной логике
        from ..optimizations import FunctionBodyOptimizer
        FunctionBodyOptimizer.remove_function_body(context, body_node, func_type, placeholder_style)
        return
    
    # Вычисляем абсолютную позицию ':'
    func_start = func_def.start_byte
    absolute_colon_pos = func_start + colon_pos
    
    # Удаляем всё от позиции после ':' до конца body
    body_start_byte, body_end_byte = context.doc.get_node_range(body_node)
    removal_start = absolute_colon_pos + 1  # После ':'
    removal_end = body_end_byte
    
    # Подсчитываем строки
    removal_start_line = _get_line_number_for_byte(context.doc, removal_start)
    body_end_line = context.doc.get_line_range(body_node)[1]
    lines_removed = body_end_line - removal_start_line + 1
    
    # Создаем плейсхолдер
    if func_type == "method":
        placeholder = context.placeholder_gen.create_method_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        context.metrics.mark_method_removed()
    else:
        placeholder = context.placeholder_gen.create_function_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        context.metrics.mark_function_removed()

    # Добавляем правку
    context.editor.add_replacement(
        removal_start, removal_end, f"\n    {placeholder}",
        type=f"{func_type}_body_removal_simple",
        is_placeholder=True,
        lines_removed=lines_removed
    )

    context.metrics.add_lines_saved(lines_removed)
    bytes_saved = removal_end - removal_start - len(f"\n    {placeholder}".encode('utf-8'))
    if bytes_saved > 0:
        context.metrics.add_bytes_saved(bytes_saved)
    context.metrics.mark_placeholder_inserted()


def remove_function_body_preserve_docstring(
        root_optimizer: FunctionBodyOptimizer,
        context: ProcessingContext,
        body_node: Node,
        func_type: str,
        placeholder_style: str
) -> None:
    """
    Удаляет тело функции/метода, сохраняя docstring, если он есть.

    Args:
        root_optimizer: Универсальный оптимизатор тел функций
        context: Контекст обработки с доступом к документу
        body_node: Узел тела функции
        func_type: Тип функции ("function" или "method")
        placeholder_style: Стиль плейсхолдера

    Returns:
        True если удаление было выполнено
    """
    # Ищем docstring в теле функции
    docstring_node = _find_docstring_in_body(body_node)

    if docstring_node is None:
        # Нет docstring - нужно удалить всё после ':' в определении функции
        # Находим function_definition, который содержит body_node
        function_def = _find_function_definition(body_node)
        if function_def is None:
            # Fallback к стандартной логике
            return root_optimizer.remove_function_body(context, body_node, func_type, placeholder_style)
        
        # Найдем позицию после ':' в определении функции
        colon_pos = _find_colon_position(context.doc, function_def)
        if colon_pos is None:
            # Fallback к стандартной логике
            return root_optimizer.remove_function_body(context, body_node, func_type, placeholder_style)
        
        # Удаляем всё от позиции после ':' до конца body
        body_start_byte, body_end_byte = context.doc.get_node_range(body_node)
        removal_start = colon_pos + 1  # После ':'
        removal_end = body_end_byte
        
        # Подсчитываем строки между : и концом body
        removal_start_line = _get_line_number_for_byte(context.doc, removal_start)
        body_end_line = context.doc.get_line_range(body_node)[1]
        lines_removed = body_end_line - removal_start_line + 1
        
        # Создаем плейсхолдер
        if func_type == "method":
            placeholder = context.placeholder_gen.create_method_placeholder(
                lines_removed=lines_removed,
                bytes_removed=removal_end - removal_start,
                style=placeholder_style
            )
            context.metrics.mark_method_removed()
        else:
            placeholder = context.placeholder_gen.create_function_placeholder(
                lines_removed=lines_removed,
                bytes_removed=removal_end - removal_start,
                style=placeholder_style
            )
            context.metrics.mark_function_removed()

        # Добавляем правку (заменяем всё после ':' на плейсхолдер с отступом)
        context.editor.add_replacement(
            removal_start, removal_end, f"\n    {placeholder}",
            type=f"{func_type}_body_removal_full",
            is_placeholder=True,
            lines_removed=lines_removed
        )

        context.metrics.add_lines_saved(lines_removed)
        bytes_saved = removal_end - removal_start - len(f"\n    {placeholder}".encode('utf-8'))
        if bytes_saved > 0:
            context.metrics.add_bytes_saved(bytes_saved)
        context.metrics.mark_placeholder_inserted()
        
        return None

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

    # Подсчитываем статистику
    removal_start_line = _get_line_number_for_byte(context.doc, removal_start)
    body_end_line = context.doc.get_line_range(body_node)[1]
    lines_removed = max(0, body_end_line - removal_start_line + 1)

    if lines_removed <= 0:
        # Нечего удалять после docstring
        return None

    # Создаем плейсхолдер
    if func_type == "method":
        placeholder = context.placeholder_gen.create_method_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        context.metrics.mark_method_removed()
    else:
        placeholder = context.placeholder_gen.create_function_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        context.metrics.mark_function_removed()

    # Добавляем правку (заменяем код после docstring на плейсхолдер)
    context.editor.add_replacement(
        removal_start, removal_end, f"\n    {placeholder}",
        type=f"{func_type}_body_removal_preserve_docstring",
        is_placeholder=True,
        lines_removed=lines_removed
    )

    context.metrics.add_lines_saved(lines_removed)
    bytes_saved = removal_end - removal_start - len(f"\n    {placeholder}".encode('utf-8'))
    if bytes_saved > 0:
        context.metrics.add_bytes_saved(bytes_saved)
    context.metrics.mark_placeholder_inserted()

    return None


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


def _get_line_number_for_byte(doc: TreeSitterDocument, byte_offset: int) -> int:
    """
    Получает номер строки (0-based) для байтового смещения.
    """
    # Простая реализация - подсчитываем переводы строк до этого байта
    text_before = doc.text_bytes[:byte_offset]
    return text_before.count(b'\n')


def _find_function_definition(body_node: Node) -> Optional[Node]:
    """
    Находит function_definition, который содержит данный body_node.

    Args:
        body_node: Узел тела функции

    Returns:
        Узел function_definition или None если не найден
    """
    current = body_node.parent
    while current:
        if current.type == "function_definition":
            return current
        current = current.parent
    return None


def _find_colon_position(doc: TreeSitterDocument, function_def: Node) -> Optional[int]:
    """
    Находит позицию символа ':' в определении функции.

    Args:
        doc: Tree-sitter документ
        function_def: Узел function_definition

    Returns:
        Байтовая позиция ':' или None если не найден
    """
    # Ищем ':' в тексте function_definition
    func_text = doc.get_node_text(function_def)
    func_start = function_def.start_byte
    
    # Простой поиск ':'
    colon_offset = func_text.find(':')
    if colon_offset == -1:
        return None
    
    return func_start + colon_offset


def _find_docstring_in_body(body_node: Node) -> Optional[Node]:
    """
    Находит docstring в теле функции (первый expression_statement со string).

    Args:
        body_node: Узел тела функции

    Returns:
        Узел docstring или None если не найден
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