"""
Python function body optimization.
"""

from ..tree_sitter_support import Node

def remove_function_body_preserve_docstring(
        body_node: Node,
        func_type: str = "function",
        placeholder_style: str = "inline"
) -> bool:
    """
    Удаляет тело функции/метода, сохраняя docstring, если он есть.

    Args:
        body_node: Узел тела функции
        func_type: Тип функции ("function" или "method")
        placeholder_style: Стиль плейсхолдера

    Returns:
        True если удаление было выполнено
    """
    # Ищем docstring в теле функции
    docstring_node = self._find_docstring_in_body(body_node)

    if docstring_node is None:
        # Нет docstring - удаляем всё содержимое после ':' в определении функции
        return self._remove_function_body_complete(body_node, func_type, placeholder_style)

    # Есть docstring - удаляем только часть после него
    docstring_end_byte = docstring_node.end_byte
    body_start_byte, body_end_byte = self.doc.get_node_range(body_node)

    # Найдём первый символ после docstring (обычно перевод строки)
    # Нужно найти следующий statement после docstring
    next_statement_start = self._find_next_statement_after_docstring(body_node, docstring_node)

    if next_statement_start is None or next_statement_start >= body_end_byte:
        # Нет кода после docstring - оставляем только docstring
        return False

    # Вычисляем что удаляем (от начала следующего statement до конца тела)
    removal_start = next_statement_start
    removal_end = body_end_byte

    # Подсчитываем статистику
    removal_start_line = self._get_line_number_for_byte(removal_start)
    body_end_line = self.doc.get_line_range(body_node)[1]
    lines_removed = max(0, body_end_line - removal_start_line + 1)

    if lines_removed <= 0:
        # Нечего удалять после docstring
        return False

    # Создаем плейсхолдер
    if func_type == "method":
        placeholder = self.placeholder_gen.create_method_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        self.metrics.mark_method_removed()
    else:
        placeholder = self.placeholder_gen.create_function_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        self.metrics.mark_function_removed()

    # Добавляем правку (заменяем код после docstring на плейсхолдер)
    self.editor.add_replacement(
        removal_start, removal_end, f"\n    {placeholder}",
        type=f"{func_type}_body_removal_preserve_docstring",
        is_placeholder=True,
        lines_removed=lines_removed
    )

    self.metrics.add_lines_saved(lines_removed)
    bytes_saved = removal_end - removal_start - len(f"\n    {placeholder}".encode('utf-8'))
    if bytes_saved > 0:
        self.metrics.add_bytes_saved(bytes_saved)
    self.metrics.mark_placeholder_inserted()

    return True


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


def _get_line_number_for_byte(byte_offset: int) -> int:
    """
    Получает номер строки (0-based) для байтового смещения.
    """
    # Простая реализация - подсчитываем переводы строк до этого байта
    text_before = self.doc._text_bytes[:byte_offset]
    return text_before.count(b'\n')


def _remove_function_body_complete(
        body_node: Node,
        func_type: str = "function",
        placeholder_style: str = "inline"
) -> bool:
    """
    Полностью удаляет тело функции, включая комментарии и всё содержимое.
    Используется когда нет docstring для сохранения.
    """
    # Найдём функцию-родителя
    function_node = self._find_function_definition(body_node)
    if function_node is None:
        # Fallback к обычному удалению body_node
        return self.remove_function_body(body_node, func_type, placeholder_style)

    # Найдём позицию ':' в определении функции
    function_text = self.doc.get_node_text(function_node)
    colon_index = function_text.find(':')
    if colon_index == -1:
        # Fallback если не нашли ':'
        return self.remove_function_body(body_node, func_type, placeholder_style)

    # Вычисляем диапазон удаления: от ':' + 1 до конца функции
    function_start_byte = function_node.start_byte
    removal_start = function_start_byte + colon_index + 1
    removal_end = function_node.end_byte

    # Подсчитываем статистику
    removal_start_line = self._get_line_number_for_byte(removal_start)
    function_end_line = self.doc.get_line_range(function_node)[1]
    lines_removed = max(0, function_end_line - removal_start_line + 1)

    if lines_removed <= 0:
        return False

    # Создаем плейсхолдер
    if func_type == "method":
        placeholder = self.placeholder_gen.create_method_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        self.metrics.mark_method_removed()
    else:
        placeholder = self.placeholder_gen.create_function_placeholder(
            lines_removed=lines_removed,
            bytes_removed=removal_end - removal_start,
            style=placeholder_style
        )
        self.metrics.mark_function_removed()

    # Заменяем всё содержимое после ':' на плейсхолдер
    self.editor.add_replacement(
        removal_start, removal_end, f"\n    {placeholder}",
        type=f"{func_type}_body_complete_removal",
        is_placeholder=True,
        lines_removed=lines_removed
    )

    self.metrics.add_lines_saved(lines_removed)
    bytes_saved = removal_end - removal_start - len(f"\n    {placeholder}".encode('utf-8'))
    if bytes_saved > 0:
        self.metrics.add_bytes_saved(bytes_saved)
    self.metrics.mark_placeholder_inserted()

    return True


def _find_function_definition(body_node: Node) -> Optional[Node]:
    """
    Находит узел function_definition для данного body узла.
    """
    current = body_node.parent
    while current:
        if current.type in ("function_definition", "method_definition"):
            return current
        current = current.parent
    return None


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