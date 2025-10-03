"""
Правила парсинга для адаптивных конструкций в шаблонах.

Обрабатывает директивы {% ... %}, комментарии {# ... #},
условные блоки if-elif-else, режимные блоки mode-endmode.
"""

from __future__ import annotations

from typing import List, Optional

from .nodes import ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode
from ..types import PluginPriority, ParsingRule, ParsingContext
from ..nodes import TemplateNode
from ..tokens import ParserError


def parse_directive(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Парсит директиву {% ... %}.
    
    Может быть условием (if), режимом (mode) или их завершением.
    
    NOTE: Текущая реализация не полностью функциональна для блочных директив (if-endif).
    Требуется переработка для корректной обработки вложенных блоков.
    """
    # Проверяем начало директивы
    if not context.match("DIRECTIVE_START"):
        return None
    
    # Потребляем {%
    context.consume("DIRECTIVE_START")
    
    # Собираем токены содержимого директивы
    content_tokens = []
    while not context.is_at_end() and not context.match("DIRECTIVE_END"):
        content_tokens.append(context.advance())
    
    if context.is_at_end():
        raise ParserError("Unexpected end of tokens, expected %}", context.current())
    
    # Потребляем %}
    context.consume("DIRECTIVE_END")
    
    # Парсим содержимое директивы
    return _parse_directive_content(content_tokens, context)


def _parse_directive_content(content_tokens: List, context: ParsingContext) -> TemplateNode:
    """Парсит содержимое директивы на основе токенов."""
    if not content_tokens:
        raise ParserError("Empty directive", context.current())
    
    # Пропускаем пробелы в начале
    non_whitespace_tokens = [t for t in content_tokens if t.type != "WHITESPACE"]
    if not non_whitespace_tokens:
        raise ParserError("Empty directive (only whitespace)", context.current())
    
    first_token = non_whitespace_tokens[0]
    keyword = first_token.value.lower()
    
    if keyword == 'if':
        return _parse_if_directive(content_tokens, context)
    elif keyword == 'elif':
        raise ParserError("elif without if", first_token)
    elif keyword == 'else':
        # Самостоятельный else не должен встречаться (обрабатывается внутри if)
        raise ParserError("else without if", first_token)
    elif keyword == 'mode':
        return _parse_mode_directive(content_tokens, context)
    elif keyword == 'endif':
        raise ParserError("endif without if", first_token)
    elif keyword == 'endmode':
        raise ParserError("endmode without mode", first_token)
    else:
        raise ParserError(f"Unknown directive: {first_token.value}", first_token)


def _parse_if_directive(content_tokens: List, context: ParsingContext) -> ConditionalBlockNode:
    """
    Парсит условную директиву {% if condition %} с поддержкой elif и else.
    """
    # Пропускаем пробелы и находим 'if'
    non_whitespace = [t for t in content_tokens if t.type != "WHITESPACE"]
    if not non_whitespace or non_whitespace[0].value.lower() != 'if':
        raise ParserError("Expected 'if' keyword", content_tokens[0] if content_tokens else context.current())
    
    # Извлекаем условие (все токены после 'if', исключая пробелы в начале и конце)
    # Находим индекс первого 'if' токена
    if_index = -1
    for i, t in enumerate(content_tokens):
        if t.type == "IDENTIFIER" and t.value.lower() == "if":
            if_index = i
            break
    
    if if_index == -1 or if_index + 1 >= len(content_tokens):
        raise ParserError("Missing condition in if directive", content_tokens[0] if content_tokens else context.current())
    
    # Берем все токены после 'if', исключая пробелы в начале
    condition_tokens = content_tokens[if_index + 1:]
    # Убираем начальные пробелы
    while condition_tokens and condition_tokens[0].type == "WHITESPACE":
        condition_tokens = condition_tokens[1:]
    
    if not condition_tokens:
        raise ParserError("Missing condition in if directive", content_tokens[if_index])
    
    condition_text = _reconstruct_condition_text(condition_tokens)
    
    # Парсим условие с помощью парсера условий
    try:
        from ...conditions.parser import ConditionParser
        condition_parser = ConditionParser()
        condition_ast = condition_parser.parse(condition_text)
    except Exception as e:
        raise ParserError(f"Invalid condition: {e}", content_tokens[0])
    
    # Парсим тело условия до elif, else или endif
    body_nodes = []
    elif_blocks = []
    else_block = None
    found_end = False
    
    while not context.is_at_end():
        # Проверяем, не встретили ли мы endif, elif или else
        if _check_directive_keyword(context, 'endif'):
            _consume_directive_keyword(context, 'endif')
            found_end = True
            break
        elif _check_directive_keyword(context, 'elif'):
            # Парсим elif блоки
            elif_blocks.extend(_parse_elif_blocks(context))
            # После парсинга всех elif блоков проверяем else
            if _check_directive_keyword(context, 'else'):
                _consume_directive_keyword(context, 'else')
                else_block = _parse_else_block(context)
            _consume_directive_keyword(context, 'endif')
            found_end = True
            break
        elif _check_directive_keyword(context, 'else'):
            _consume_directive_keyword(context, 'else')
            else_block = _parse_else_block(context)
            _consume_directive_keyword(context, 'endif')
            found_end = True
            break
        
        # Парсим следующий узел (рекурсивно применяем все правила парсинга)
        # Используем вспомогательную функцию для парсинга произвольного узла
        node = _parse_any_node(context)
        if node:
            body_nodes.append(node)
        else:
            # Если не удалось распарсить узел, обрабатываем как текст
            token = context.advance()
            from ..nodes import TextNode
            body_nodes.append(TextNode(text=token.value))
    
    if not found_end:
        raise ParserError("Unexpected end of tokens, expected {% endif %}", content_tokens[0])
    
    return ConditionalBlockNode(
        condition_text=condition_text,
        body=body_nodes,
        elif_blocks=elif_blocks,
        else_block=else_block,
        condition_ast=condition_ast
    )


def _parse_elif_blocks(context: ParsingContext) -> List[ElifBlockNode]:
    """
    Парсит последовательность elif блоков.
    """
    elif_blocks = []
    
    while _check_directive_keyword(context, 'elif'):
        # Потребляем {%
        context.consume("DIRECTIVE_START")
        
        # Собираем токены содержимого elif директивы
        content_tokens = []
        while not context.is_at_end() and not context.match("DIRECTIVE_END"):
            content_tokens.append(context.advance())
        
        # Потребляем %}
        context.consume("DIRECTIVE_END")
        
        # Парсим содержимое elif директивы
        elif_block = _parse_single_elif_directive(content_tokens, context)
        elif_blocks.append(elif_block)
    
    return elif_blocks


def _parse_single_elif_directive(content_tokens: List, context: ParsingContext) -> ElifBlockNode:
    """Парсит одну elif директиву из уже извлеченных токенов содержимого."""
    if not content_tokens or content_tokens[0].value.lower() != 'elif':
        raise ParserError("Expected 'elif' keyword", content_tokens[0] if content_tokens else context.current())
    
    # Извлекаем условие (все токены после 'elif')
    if len(content_tokens) < 2:
        raise ParserError("Missing condition in elif directive", content_tokens[0])
    
    condition_tokens = content_tokens[1:]
    condition_text = _reconstruct_condition_text(condition_tokens)
    
    # Парсим условие с помощью парсера условий
    try:
        from ...conditions.parser import ConditionParser
        condition_parser = ConditionParser()
        condition_ast = condition_parser.parse(condition_text)
    except Exception as e:
        raise ParserError(f"Invalid elif condition: {e}", content_tokens[0])
    
    # Парсим тело elif блока
    elif_body = []
    while not context.is_at_end():
        if (_check_directive_keyword(context, 'elif') or 
            _check_directive_keyword(context, 'else') or 
            _check_directive_keyword(context, 'endif')):
            break
        
        node = _parse_any_node(context)
        if node:
            elif_body.append(node)
        else:
            # Если не удалось распарсить узел, обрабатываем как текст
            token = context.advance()
            from ..nodes import TextNode
            elif_body.append(TextNode(text=token.value))
    
    return ElifBlockNode(
        condition_text=condition_text,
        body=elif_body,
        condition_ast=condition_ast
    )


def _parse_else_block(context: ParsingContext) -> ElseBlockNode:
    """Парсит тело else блока."""
    else_body = []
    
    while not context.is_at_end():
        if _check_directive_keyword(context, 'endif'):
            break
        
        node = _parse_any_node(context)
        if node:
            else_body.append(node)
        else:
            # Если не удалось распарсить узел, обрабатываем как текст
            token = context.advance()
            from ..nodes import TextNode
            else_body.append(TextNode(text=token.value))
    
    return ElseBlockNode(body=else_body)


def _parse_mode_directive(content_tokens: List, context: ParsingContext) -> ModeBlockNode:
    """
    Парсит режимную директиву {% mode modeset:mode %}.
    """
    # Ожидаем формат: mode modeset:mode_name
    if len(content_tokens) < 2:
        raise ParserError("Missing mode specification in mode directive", content_tokens[0])
    
    # Собираем спецификацию режима (все токены после 'mode')
    mode_spec_tokens = content_tokens[1:]
    mode_spec = ''.join(t.value for t in mode_spec_tokens)
    
    # Парсим спецификацию режима (формат: modeset:mode)
    if ':' not in mode_spec:
        raise ParserError(
            f"Invalid mode specification '{mode_spec}'. Expected format: modeset:mode",
            content_tokens[1]
        )
    
    parts = mode_spec.split(':', 1)
    modeset = parts[0].strip()
    mode = parts[1].strip()
    
    if not modeset or not mode:
        raise ParserError(
            f"Invalid mode specification '{mode_spec}'. Both modeset and mode must be non-empty",
            content_tokens[1]
        )
    
    # Парсим тело режимного блока до endmode
    body_nodes = []
    found_end = False
    
    while not context.is_at_end():
        if _check_directive_keyword(context, 'endmode'):
            _consume_directive_keyword(context, 'endmode')
            found_end = True
            break
        
        node = _parse_any_node(context)
        if node:
            body_nodes.append(node)
        else:
            # Если не удалось распарсить узел, обрабатываем как текст
            token = context.advance()
            from ..nodes import TextNode
            body_nodes.append(TextNode(text=token.value))
    
    if not found_end:
        raise ParserError("Unexpected end of tokens, expected {% endmode %}", content_tokens[0])
    
    return ModeBlockNode(
        modeset=modeset,
        mode=mode,
        body=body_nodes
    )


def parse_comment(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Парсит комментарий {# ... #}.
    """
    # Проверяем начало комментария
    if not context.match("COMMENT_START"):
        return None
    
    # Сохраняем позицию для отката в случае ошибки
    saved_position = context.position
    
    try:
        # Потребляем {#
        context.consume("COMMENT_START")
        
        # Собираем текст комментария
        comment_parts = []
        while not context.is_at_end() and not context.match("COMMENT_END"):
            comment_parts.append(context.advance().value)
        
        if context.is_at_end():
            raise ParserError("Unexpected end of tokens, expected #}", context.current())
        
        # Потребляем #}
        context.consume("COMMENT_END")
        
        comment_text = ''.join(comment_parts)
        return CommentNode(text=comment_text)
        
    except (ParserError, Exception):
        # Откатываемся при ошибке
        context.position = saved_position
        return None


# Вспомогательные функции

def _reconstruct_condition_text(tokens: List) -> str:
    """
    Реконструирует текст условия из токенов с правильными пробелами.
    """
    if not tokens:
        return ""
    
    parts = []
    for i, token in enumerate(tokens):
        # Добавляем пробел перед токеном, если это не первый токен
        # и если это не специальный символ, который должен прилипать
        if i > 0:
            prev_token = tokens[i - 1]
            # НЕ добавляем пробел перед или после двоеточия :
            # НЕ добавляем пробел перед или после скобок ( )
            if not (token.value in [":", "(", ")"] or 
                   prev_token.value in [":", "(", ")"]):
                parts.append(" ")
        
        parts.append(token.value)
    
    return ''.join(parts)


def _check_directive_keyword(context: ParsingContext, keyword: str) -> bool:
    """
    Проверяет, является ли следующая конструкция директивой с указанным ключевым словом.
    """
    if not context.match("DIRECTIVE_START"):
        return False
    
    # Смотрим вперед, не меняя позицию
    next_token = context.peek(1)  # Токен после {%
    return next_token.value.lower() == keyword


def _consume_directive_keyword(context: ParsingContext, keyword: str) -> None:
    """
    Потребляет директиву с указанным ключевым словом.
    """
    context.consume("DIRECTIVE_START")
    
    # Собираем токены до %}
    found_keyword = False
    while not context.is_at_end() and not context.match("DIRECTIVE_END"):
        token = context.advance()
        if token.value.lower() == keyword:
            found_keyword = True
    
    if not found_keyword:
        raise ParserError(f"Expected '{keyword}' directive", context.current())
    
    context.consume("DIRECTIVE_END")


def _parse_any_node(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Пытается распарсить произвольный узел, применяя все зарегистрированные правила.
    
    Эта функция делегирует парсинг к главному парсеру через обработчики плагина.
    """
    # Получаем обработчики из глобального состояния (будет установлено плагином)
    handlers = getattr(_parse_any_node, '_handlers', None)
    if handlers is None:
        # Если обработчики не установлены, возвращаем None
        return None
    
    # Делегируем парсинг к главному парсеру
    return handlers.parse_next_node(context)


def get_adaptive_parser_rules() -> List[ParsingRule]:
    """
    Возвращает правила парсинга для адаптивных конструкций.
    """
    return [
        ParsingRule(
            name="parse_directive",
            priority=PluginPriority.DIRECTIVE,
            parser_func=parse_directive
        ),
        ParsingRule(
            name="parse_comment",
            priority=PluginPriority.COMMENT,
            parser_func=parse_comment
        )
    ]


def set_parser_handlers(handlers) -> None:
    """
    Устанавливает обработчики для использования в правилах парсинга.
    
    Вызывается плагином после инициализации для обеспечения
    рекурсивного парсинга вложенных структур.
    
    Args:
        handlers: Обработчики ядра шаблонизатора
    """
    _parse_any_node._handlers = handlers


__all__ = ["get_adaptive_parser_rules", "set_parser_handlers"]

