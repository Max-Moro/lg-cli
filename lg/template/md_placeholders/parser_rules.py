"""
Правила парсинга для Markdown-плейсхолдеров.

Обрабатывает конструкции вида:
- ${md:path}
- ${md:path#anchor}
- ${md:path,level:3,strip_h1:true}
- ${md@origin:path}
- ${md@[origin]:path}
- ${md:docs/*}
- ${md:path,if:tag:python}
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from .nodes import MarkdownFileNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import PluginPriority, ParsingRule, ParsingContext


def parse_md_placeholder(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Парсит MD-плейсхолдер ${md:...}.
    
    Возвращает MarkdownFileNode если распознан MD-плейсхолдер, иначе None.
    """
    # Проверяем начало плейсхолдера
    if not context.match("PLACEHOLDER_START"):
        return None
    
    # Сохраняем позицию для отката
    saved_position = context.position
    
    # Потребляем ${
    context.consume("PLACEHOLDER_START")
    
    # Проверяем префикс 'md' через IDENTIFIER
    if not context.match("IDENTIFIER"):
        context.position = saved_position
        return None
    
    first_token = context.current()
    if first_token.value != 'md':
        context.position = saved_position
        return None
    
    # Теперь мы уверены что это MD-плейсхолдер - любые ошибки дальше должны пробрасываться!
    context.advance()  # Потребляем 'md'
    
    # Парсим содержимое плейсхолдера (НЕ ловим исключения - пусть летят наверх)
    node = _parse_md_content(context)
    
    # Потребляем }
    context.consume("PLACEHOLDER_END")
    
    return node


def _parse_md_content(context: ParsingContext) -> MarkdownFileNode:
    """
    Парсит содержимое MD-плейсхолдера после 'md'.
    
    Определяет тип (простой/адресный) и создает MarkdownFileNode.
    """
    # Проверяем, адресное это включение или простое
    if context.match("AT"):
        # Адресное включение: md@origin:path[,params...]
        return _parse_addressed_md(context)
    elif context.match("COLON"):
        # Простое включение: md:path[,params...]
        return _parse_simple_md(context)
    else:
        raise ParserError(f"Expected ':' or '@' after 'md'", context.current())


def _parse_simple_md(context: ParsingContext) -> MarkdownFileNode:
    """
    Парсит простое MD-включение: md:path[#anchor][,params...]
    """
    context.consume("COLON")  # Потребляем :
    
    # Парсим путь, якорь и параметры
    path, anchor, params = _parse_path_anchor_params(context)
    
    # Определяем, содержит ли путь глобы
    is_glob = _path_contains_globs(path)
    
    return MarkdownFileNode(
        path=path,
        origin=None,  # Для обычных md: origin не задан
        heading_level=params.get('level'),
        strip_h1=params.get('strip_h1'),
        anchor=anchor,
        condition=params.get('if'),
        is_glob=is_glob
    )


def _parse_addressed_md(context: ParsingContext) -> MarkdownFileNode:
    """
    Парсит адресное MD-включение: md@origin:path[#anchor][,params...]
    или md@[origin]:path[#anchor][,params...]
    """
    context.consume("AT")  # Потребляем @
    
    # Парсим origin
    origin = _parse_origin(context)
    
    # Потребляем :
    context.consume("COLON")
    
    # Парсим путь, якорь и параметры
    path, anchor, params = _parse_path_anchor_params(context)
    
    # Определяем, содержит ли путь глобы
    is_glob = _path_contains_globs(path)
    
    return MarkdownFileNode(
        path=path,
        origin=origin,
        heading_level=params.get('level'),
        strip_h1=params.get('strip_h1'),
        anchor=anchor,
        condition=params.get('if'),
        is_glob=is_glob
    )


def _parse_origin(context: ParsingContext) -> str:
    """
    Парсит origin в адресном MD-плейсхолдере.
    
    Поддерживает:
    - origin (простая форма)
    - [origin] (скобочная форма для путей с двоеточиями)
    """
    # Проверяем скобочную форму
    if context.match("LBRACKET"):
        context.advance()  # Потребляем [
        
        # Собираем origin внутри скобок
        origin_parts = []
        while not context.match("RBRACKET") and not context.is_at_end():
            token = context.advance()
            origin_parts.append(token.value)
        
        if context.is_at_end():
            raise ParserError("Expected ']' to close bracketed origin", context.current())
        
        context.consume("RBRACKET")  # Потребляем ]
        
        return "".join(origin_parts)
    
    # Простая форма - собираем до двоеточия
    origin_parts = []
    while not context.match("COLON") and not context.is_at_end():
        # Останавливаемся на специальных токенах
        if context.match("PLACEHOLDER_END", "COMMA", "HASH"):
            break
        token = context.advance()
        origin_parts.append(token.value)
    
    if not origin_parts:
        raise ParserError("Empty origin in MD reference", context.current())
    
    return "".join(origin_parts)


def _parse_path_anchor_params(context: ParsingContext) -> Tuple[str, Optional[str], dict]:
    """
    Парсит путь, якорь и параметры из текущей позиции.
    
    Формат: path[#anchor][,param:value,...]
    
    Returns:
        Кортеж (path, anchor, params_dict)
    """
    # Парсим путь
    path = _parse_file_path(context)
    
    # Парсим якорь если есть
    anchor = None
    if context.match("HASH"):
        context.advance()  # Потребляем #
        anchor = _parse_anchor(context)
    
    # Парсим параметры если есть
    params = {}
    while context.match("COMMA"):
        context.advance()  # Потребляем ,
        
        param_name, param_value = _parse_parameter(context)
        params[param_name] = param_value
    
    return path, anchor, params


def _parse_file_path(context: ParsingContext) -> str:
    """
    Парсит путь к файлу, включая поддержку глобов и слешей.
    
    Returns:
        Строка пути (например, "docs/api" или "docs/*.md")
    """
    path_parts = []
    
    while not context.is_at_end():
        current = context.current()
        
        # Останавливаемся на специальных токенах
        if current.type in ("HASH", "COMMA", "PLACEHOLDER_END"):
            break
        
        # Добавляем токен к пути
        if current.type in ("IDENTIFIER", "GLOB_STAR", "TEXT"):
            path_parts.append(current.value)
            context.advance()
        elif current.value in ("/", ".", "-", "_"):
            # Разрешенные символы в пути
            path_parts.append(current.value)
            context.advance()
        else:
            # Неожиданный токен - останавливаемся
            break
    
    if not path_parts:
        raise ParserError("Expected file path", context.current())
    
    return "".join(path_parts)


def _parse_anchor(context: ParsingContext) -> str:
    """
    Парсит якорь после #.
    
    Returns:
        Строка якоря (название заголовка)
    """
    anchor_parts = []
    
    while not context.is_at_end():
        current = context.current()
        
        # Останавливаемся на разделителях
        if current.type in ("COMMA", "PLACEHOLDER_END"):
            break
        
        # Добавляем токен к якорю
        anchor_parts.append(current.value)
        context.advance()
    
    if not anchor_parts:
        raise ParserError("Expected anchor name after '#'", context.current())
    
    return "".join(anchor_parts).strip()


def _parse_parameter(context: ParsingContext) -> Tuple[str, Any]:
    """
    Парсит один параметр вида name:value.
    
    Returns:
        Кортеж (param_name, param_value)
    """
    # Пропускаем пробелы перед именем параметра
    while context.match("WHITESPACE"):
        context.advance()
    
    # Парсим имя параметра через IDENTIFIER (включая 'if')
    if not context.match("IDENTIFIER"):
        raise ParserError("Expected parameter name", context.current())
    
    param_token = context.advance()
    param_name = param_token.value
    
    # Потребляем двоеточие
    context.consume("COLON")
    
    # Пропускаем пробелы после двоеточия
    while context.match("WHITESPACE"):
        context.advance()
    
    # Парсим значение параметра
    if param_name == 'if':
        # Для 'if' собираем всё до запятой или конца как условие
        param_value = _parse_condition_value(context)
    elif param_name == 'level':
        # Числовые параметры
        param_value = _parse_number_value(context)
    elif param_name == 'strip_h1':
        # Булевы параметры
        param_value = _parse_bool_value(context)
    elif param_name == 'anchor':
        # Якорь для частичного включения
        param_value = _parse_string_value(context)
        if not param_value.strip():
            raise ParserError("Anchor cannot be empty", param_token)
    else:
        # Неизвестный параметр - вызываем ошибку
        raise ParserError(
            f"Unknown parameter '{param_name}'. Supported parameters: level, strip_h1, if, anchor",
            param_token
        )
    
    return param_name, param_value


def _parse_condition_value(context: ParsingContext) -> str:
    """
    Парсит значение условия для параметра 'if'.
    
    Собирает все токены до запятой или конца плейсхолдера.
    """
    value_parts = []
    
    while not context.is_at_end():
        current = context.current()
        
        # Останавливаемся на разделителях
        if current.type in ("COMMA", "PLACEHOLDER_END"):
            break
        
        # Добавляем пробел перед токеном (если не первый и не специальный)
        if value_parts and current.value not in (":", "(", ")"):
            prev_value = value_parts[-1] if value_parts else ""
            if prev_value not in (":", "(", ")"):
                value_parts.append(" ")
        
        value_parts.append(current.value)
        context.advance()
    
    if not value_parts:
        raise ParserError("Expected condition value after 'if:'", context.current())
    
    return "".join(value_parts)


def _parse_number_value(context: ParsingContext) -> int:
    """Парсит числовое значение параметра."""
    if not context.match("NUMBER"):
        raise ParserError("Expected number value", context.current())
    
    token = context.advance()
    try:
        value = int(token.value)
        # Валидация диапазона для level (должно быть от 1 до 6)
        if not 1 <= value <= 6:
            raise ParserError(f"Level must be between 1 and 6, got {value}", token)
        return value
    except ValueError:
        raise ParserError(f"Invalid number: {token.value}", token)


def _parse_bool_value(context: ParsingContext) -> bool:
    """Парсит булево значение параметра."""
    current = context.current()
    
    if current.type == "BOOL_TRUE":
        context.advance()
        return True
    elif current.type == "BOOL_FALSE":
        context.advance()
        return False
    elif current.type == "NUMBER":
        # Числа 1 и 0 как булевы значения
        value = current.value
        context.advance()
        if value == "1":
            return True
        elif value == "0":
            return False
        else:
            raise ParserError(f"Boolean number must be 0 or 1, got '{value}'", current)
    elif current.type == "IDENTIFIER":
        # Fallback для обычных идентификаторов
        value = current.value.lower()
        context.advance()
        if value in ("true", "yes"):
            return True
        elif value in ("false", "no"):
            return False
    
    raise ParserError(f"Expected boolean value (true/false/1/0/yes/no)", current)


def _parse_string_value(context: ParsingContext) -> str:
    """Парсит строковое значение параметра."""
    value_parts = []
    
    # Собираем значение до запятой или конца, включая возможные двоеточия
    while not context.is_at_end():
        current = context.current()
        
        # Останавливаемся на разделителях
        if current.type in ("COMMA", "PLACEHOLDER_END"):
            break
        
        value_parts.append(current.value)
        context.advance()
    
    if not value_parts:
        raise ParserError("Expected parameter value", context.current())
    
    return "".join(value_parts)


def _path_contains_globs(path: str) -> bool:
    """
    Проверяет, содержит ли путь глоб-паттерны.
    
    Args:
        path: Путь для проверки
        
    Returns:
        True если путь содержит * или **
    """
    return '*' in path


def get_md_parser_rules() -> List[ParsingRule]:
    """
    Возвращает правила парсинга для MD-плейсхолдеров.
    """
    return [
        ParsingRule(
            name="parse_md_placeholder",
            priority=PluginPriority.PLACEHOLDER,  # Тот же приоритет что у обычных плейсхолдеров
            parser_func=parse_md_placeholder
        )
    ]


__all__ = ["get_md_parser_rules"]
