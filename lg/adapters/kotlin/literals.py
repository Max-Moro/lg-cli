"""
Kotlin-специфичная обработка литералов.
Включает поддержку коллекций (listOf, mapOf, setOf) и строковых шаблонов.
"""

from __future__ import annotations

from ..context import ProcessingContext
from ..tree_sitter_support import Node, TreeSitterDocument

# Kotlin коллекционные функции, которые создают литеральные данные
KOTLIN_COLLECTION_FUNCTIONS = {
    "listOf", "mutableListOf", "arrayListOf",
    "setOf", "mutableSetOf", "hashSetOf", "linkedSetOf",
    "mapOf", "mutableMapOf", "hashMapOf", "linkedMapOf",
}


def is_collection_literal(node: Node, doc: TreeSitterDocument) -> bool:
    """
    Проверяет, является ли нода вызовом коллекционной функции Kotlin.
    
    Args:
        node: Нода для проверки
        doc: Tree-sitter документ
        
    Returns:
        True если это вызов listOf/mapOf/setOf и т.п.
    """
    if node.type != "call_expression":
        return False
    
    # Ищем имя функции (первый дочерний identifier)
    for child in node.children:
        if child.type == "identifier":
            func_name = doc.get_node_text(child)
            return func_name in KOTLIN_COLLECTION_FUNCTIONS
    
    return False


def get_collection_type(node: Node, doc: TreeSitterDocument) -> str:
    """
    Определяет тип коллекции (list, map, set).
    
    Args:
        node: Нода вызова коллекции
        doc: Tree-sitter документ
        
    Returns:
        Тип коллекции ("list", "map", "set") или "collection"
    """
    for child in node.children:
        if child.type == "identifier":
            func_name = doc.get_node_text(child)
            if "list" in func_name.lower():
                return "list"
            elif "map" in func_name.lower():
                return "map"
            elif "set" in func_name.lower():
                return "set"
    
    return "collection"


def get_value_arguments_node(node: Node) -> Node | None:
    """
    Находит ноду value_arguments в вызове функции.
    
    Args:
        node: Нода call_expression
        
    Returns:
        Нода value_arguments или None
    """
    for child in node.children:
        if child.type == "value_arguments":
            return child
    return None


def process_kotlin_collection_literal(
    context: ProcessingContext,
    node: Node,
    max_tokens: int
) -> None:
    """
    Обрабатывает коллекционный литерал Kotlin (listOf/mapOf/setOf).
    
    Применяет умную обрезку содержимого с сохранением структуры.
    
    Args:
        context: Контекст обработки
        node: Нода call_expression
        max_tokens: Максимальное количество токенов
    """
    # Получаем полный текст вызова
    full_text = context.doc.get_node_text(node)
    token_count = context.tokenizer.count_text(full_text)
    
    # Если не превышает лимит - пропускаем
    if token_count <= max_tokens:
        return
    
    # Определяем тип коллекции
    collection_type = get_collection_type(node, context.doc)
    
    # Находим аргументы
    value_args = get_value_arguments_node(node)
    if not value_args:
        return
    
    # Получаем все value_argument ноды
    arguments = [child for child in value_args.children if child.type == "value_argument"]
    
    if not arguments:
        return
    
    # Вычисляем сколько аргументов можем оставить
    # Резервируем токены на имя функции, скобки и плейсхолдер
    func_name_text = full_text.split('(')[0]
    overhead = context.tokenizer.count_text(func_name_text + '("…")' )
    content_budget = max(10, max_tokens - overhead)
    
    # Определяем, многострочный ли это вызов (до выбора аргументов)
    is_multiline = '\n' in full_text
    
    # Выбираем аргументы, которые помещаются в бюджет
    included_args = []
    current_tokens = 0
    
    for arg in arguments:
        arg_text = context.doc.get_node_text(arg)
        arg_tokens = context.tokenizer.count_text(arg_text + ", ")
        
        if current_tokens + arg_tokens <= content_budget:
            included_args.append(arg)
            current_tokens += arg_tokens
        else:
            break
    
    # Если не можем включить ни один аргумент - используем только плейсхолдер
    if not included_args:
        start_char, end_char = context.doc.get_node_range(node)
        
        # Формируем минимальную замену - только плейсхолдер
        if is_multiline:
            # Многострочный формат
            base_indent = _get_line_indent_at_position(context.raw_text, start_char)
            element_indent = base_indent + "    "
            placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
            replacement = f'{func_name_text}(\n{element_indent}{placeholder}\n{base_indent})'
        else:
            # Однострочный формат
            placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
            replacement = f'{func_name_text}({placeholder})'
        
        context.editor.add_replacement(
            start_char, end_char, replacement,
            edit_type="literal_trimmed"
        )
        
        _add_savings_comment(context, node, full_text, replacement, collection_type)
        
        # Обновляем метрики
        context.metrics.mark_element_removed("literal")
        context.metrics.add_chars_saved(len(full_text) - len(replacement))
        return
    
    # Формируем замену с включенными аргументами и плейсхолдером
    start_char, end_char = context.doc.get_node_range(node)
    
    if is_multiline:
        # Многострочный формат
        replacement = _build_multiline_replacement(
            context, node, func_name_text, included_args, collection_type
        )
    else:
        # Однострочный формат
        replacement = _build_inline_replacement(
            context, included_args, func_name_text, collection_type
        )
    
    # Применяем замену
    context.editor.add_replacement(
        start_char, end_char, replacement,
        edit_type="literal_trimmed"
    )
    
    # Добавляем комментарий об экономии
    _add_savings_comment(context, node, full_text, replacement, collection_type)
    
    # Обновляем метрики
    context.metrics.mark_element_removed("literal")
    context.metrics.add_chars_saved(len(full_text) - len(replacement))


def _build_inline_replacement(
    context: ProcessingContext,
    included_args: list[Node],
    func_name: str,
    collection_type: str
) -> str:
    """Строит однострочную замену для коллекции."""
    args_texts = []
    for arg in included_args:
        arg_text = context.doc.get_node_text(arg)
        args_texts.append(arg_text)
    
    # Добавляем плейсхолдер
    placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
    args_texts.append(placeholder)
    
    return f'{func_name}({", ".join(args_texts)})'


def _build_multiline_replacement(
    context: ProcessingContext,
    node: Node,
    func_name: str,
    included_args: list[Node],
    collection_type: str
) -> str:
    """Строит многострочную замену для коллекции с правильными отступами."""
    # Базовый отступ (отступ строки с началом вызова)
    start_byte = node.start_byte
    base_indent = _get_line_indent_at_position(context.raw_text, start_byte)
    
    # Отступ для элементов (определяем из первого аргумента или добавляем 4 пробела)
    if included_args:
        element_indent = _detect_element_indent(context, included_args[0])
    else:
        element_indent = base_indent + "    "
    
    # Формируем строки
    result_lines = [f'{func_name}(']
    
    for i, arg in enumerate(included_args):
        arg_text = context.doc.get_node_text(arg)
        # Убедимся, что после каждого элемента стоит запятая
        if not arg_text.strip().endswith(','):
            arg_text = arg_text + ','
        result_lines.append(f'{element_indent}{arg_text}')
    
    # Добавляем плейсхолдер (без запятой в конце - Kotlin trailing comma опционально)
    placeholder = '"…"' if collection_type in ("list", "set") else '"…" to "…"'
    result_lines.append(f'{element_indent}{placeholder}')
    result_lines.append(f'{base_indent})')
    
    return '\n'.join(result_lines)


def _get_line_indent_at_position(text: str, byte_pos: int) -> str:
    """
    Возвращает отступ строки, на которой находится указанная байтовая позиция.
    
    Args:
        text: Исходный текст
        byte_pos: Байтовая позиция
        
    Returns:
        Строка с отступом (пробелы/табы)
    """
    # Находим начало строки
    line_start = text.rfind('\n', 0, byte_pos)
    if line_start == -1:
        line_start = 0
    else:
        line_start += 1  # Пропускаем сам символ \n
    
    # Собираем отступ
    indent = ""
    for i in range(line_start, len(text)):
        if text[i] in ' \t':
            indent += text[i]
        else:
            break
    
    return indent


def _detect_element_indent(context: ProcessingContext, arg_node: Node) -> str:
    """Определяет отступ элемента из позиции аргумента."""
    return _get_line_indent_at_position(context.raw_text, arg_node.start_byte)


def _add_savings_comment(
    context: ProcessingContext,
    node: Node,
    original_text: str,
    replacement: str,
    collection_type: str
) -> None:
    """Добавляет комментарий об экономии токенов после литерала."""

    # Вычисляем экономию токенов
    original_tokens = context.tokenizer.count_text(original_text)
    replacement_tokens = context.tokenizer.count_text(replacement)
    saved_tokens = original_tokens - replacement_tokens
    
    # Если нет экономии - не добавляем комментарий
    if saved_tokens <= 0:
        return
    
    # Определяем тип литерала для комментария
    literal_type_name = {
        "list": "array",
        "set": "set",
        "map": "object",
        "collection": "collection"
    }.get(collection_type, "literal")
    
    # Формируем текст комментария
    comment_text = f" // literal {literal_type_name} (−{saved_tokens} tokens)"
    
    # Находим конец литерала и место для вставки комментария
    end_char = node.end_byte
    
    # Проверяем, что после литерала идет
    text_after = context.raw_text[end_char:min(end_char + 100, len(context.raw_text))]
    
    # Ищем конец строки или точку с запятой
    # Если после литерала идет закрывающая скобка или запятая, вставляем после неё
    for i, char in enumerate(text_after):
        if char in ('\n', '\r'):
            insertion_offset = i
            break
        elif char == ';':
            insertion_offset = i + 1
            break
        elif char == ',':
            insertion_offset = i + 1
            break
        elif char == ')':
            _ = i + 1  # Continue scanning for ; or , after )
            continue
    else:
        # Если не нашли перевод строки в первых 100 символах, вставляем сразу
        insertion_offset = min(20, len(text_after))
    
    insertion_pos = end_char + insertion_offset
    
    # Добавляем комментарий
    context.editor.add_insertion(
        insertion_pos,
        comment_text,
        edit_type="literal_comment"
    )


def process_kotlin_literals(context: ProcessingContext, max_tokens: int | None) -> None:
    """
    Обрабатывает Kotlin-специфичные литералы (коллекции).
    
    Этот метод вызывается через хук из базового LiteralOptimizer
    для обработки специфичных для Kotlin конструкций.
    
    Args:
        context: Контекст обработки
        max_tokens: Максимальное количество токенов для литерала
    """
    if max_tokens is None:
        return
    
    # Находим все вызовы функций, исключая вложенные
    def find_top_level_collection_calls(node: Node, inside_collection: bool = False):
        """
        Находит только top-level вызовы коллекционных функций.
        Не рекурсирует внутрь найденных коллекций, чтобы избежать двойной обработки.
        """
        calls = []
        
        # Если это коллекция
        if is_collection_literal(node, context.doc):
            # Если мы НЕ внутри другой коллекции - добавляем
            if not inside_collection:
                calls.append(node)
                # Теперь помечаем, что мы внутри коллекции для детей
                inside_collection = True
        
        # Рекурсивно обходим детей
        for child in node.children:
            calls.extend(find_top_level_collection_calls(child, inside_collection))
        
        return calls
    
    # Находим только top-level коллекционные литералы
    collection_calls = find_top_level_collection_calls(context.doc.root_node)
    
    # Обрабатываем каждый вызов
    for call_node in collection_calls:
        process_kotlin_collection_literal(context, call_node, max_tokens)
