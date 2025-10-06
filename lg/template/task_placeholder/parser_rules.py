"""
Правила парсинга для task-плейсхолдеров.

Обрабатывает:
- ${task}
- ${task:prompt:"default text"}
"""

from __future__ import annotations

from typing import List, Optional

from .nodes import TaskNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import PluginPriority, ParsingRule, ParsingContext


def parse_task_placeholder(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Парсит task-плейсхолдер ${task} или ${task:prompt:"..."}.
    """
    # Проверяем начало плейсхолдера
    if not context.match("PLACEHOLDER_START"):
        return None
    
    # Сохраняем позицию для отката
    saved_position = context.position
    
    # Потребляем ${
    context.consume("PLACEHOLDER_START")
    
    # Пропускаем пробелы
    while context.match("WHITESPACE"):
        context.advance()
    
    # Проверяем ключевое слово 'task' через IDENTIFIER
    if not context.match("IDENTIFIER"):
        context.position = saved_position
        return None
    
    task_token = context.current()
    if task_token.value != "task":
        context.position = saved_position
        return None
    
    # Теперь мы уверены что это task-плейсхолдер
    context.advance()  # Потребляем 'task'
    
    # Пропускаем пробелы
    while context.match("WHITESPACE"):
        context.advance()
    
    # Проверяем наличие :prompt:"..."
    default_prompt = None
    if context.match("COLON"):
        context.advance()  # Потребляем :
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
        
        # Ожидаем 'prompt'
        if not context.match("IDENTIFIER"):
            raise ParserError("Expected 'prompt' after ':' in task placeholder", context.current())
        
        prompt_token = context.current()
        if prompt_token.value != "prompt":
            raise ParserError("Expected 'prompt' after ':' in task placeholder", prompt_token)
        context.advance()
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
        
        # Ожидаем :
        if not context.match("COLON"):
            raise ParserError("Expected ':' after 'prompt' in task placeholder", context.current())
        context.advance()
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
        
        # Ожидаем строковый литерал
        if not context.match("STRING_LITERAL"):
            raise ParserError("Expected string literal after 'prompt:' in task placeholder", context.current())
        
        string_token = context.advance()
        # Парсим строковый литерал (убираем кавычки и обрабатываем escape-последовательности)
        default_prompt = _parse_string_literal(string_token.value)
        
        # Пропускаем пробелы
        while context.match("WHITESPACE"):
            context.advance()
    
    # Потребляем }
    if not context.match("PLACEHOLDER_END"):
        raise ParserError("Expected '}' to close task placeholder", context.current())
    context.consume("PLACEHOLDER_END")
    
    return TaskNode(default_prompt=default_prompt)


def _parse_string_literal(literal: str) -> str:
    """
    Парсит строковый литерал, убирая кавычки и обрабатывая escape-последовательности.
    
    Args:
        literal: Строка вида "text" с возможными escape-последовательностями
        
    Returns:
        Обработанная строка
    """
    # Убираем окружающие кавычки
    if literal.startswith('"') and literal.endswith('"'):
        literal = literal[1:-1]
    
    # Обрабатываем escape-последовательности
    result = []
    i = 0
    while i < len(literal):
        if literal[i] == '\\' and i + 1 < len(literal):
            next_char = literal[i + 1]
            if next_char == 'n':
                result.append('\n')
            elif next_char == 't':
                result.append('\t')
            elif next_char == 'r':
                result.append('\r')
            elif next_char == '\\':
                result.append('\\')
            elif next_char == '"':
                result.append('"')
            else:
                # Неизвестная escape-последовательность - оставляем как есть
                result.append('\\')
                result.append(next_char)
            i += 2
        else:
            result.append(literal[i])
            i += 1
    
    return ''.join(result)


def get_task_parser_rules() -> List[ParsingRule]:
    """
    Возвращает правила парсинга для task-плейсхолдеров.
    
    Приоритет выше обычных PLACEHOLDER (95 > 90), чтобы
    task-плейсхолдеры обрабатывались раньше общих секций.
    """
    return [
        ParsingRule(
            name="parse_task_placeholder",
            priority=95,  # Выше PLACEHOLDER (90), но ниже DIRECTIVE (100)
            parser_func=parse_task_placeholder
        )
    ]


__all__ = ["get_task_parser_rules"]