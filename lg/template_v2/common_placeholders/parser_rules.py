"""
Правила парсинга для базовых плейсхолдеров секций и шаблонов.

Обрабатывает конструкции вида:
- ${section_name}
- ${tpl:template_name}  
- ${ctx:context_name}
- ${@origin:name} (адресные ссылки)
- ${tpl@[origin]:name} (скобочная форма адресации)
"""

from __future__ import annotations

from typing import List, Optional

from .nodes import SectionNode, IncludeNode
from ..base import ParsingContext, ParsingRule, PluginPriority
from ..nodes import TemplateNode
from ..tokens import DynamicTokenType, ParserError


def parse_placeholder(context: ParsingContext) -> Optional[TemplateNode]:
    """
    Парсит плейсхолдер ${...}.
    
    Возвращает SectionNode или IncludeNode в зависимости от содержимого.
    """
    # Проверяем начало плейсхолдера
    if not context.match(DynamicTokenType("PLACEHOLDER_START")):
        return None
    
    # Сохраняем позицию для отката в случае ошибки
    context.save_position()
    
    try:
        # Потребляем ${
        context.consume(DynamicTokenType("PLACEHOLDER_START"))
        
        # Пропускаем пробелы
        _skip_whitespace(context)
        
        # Парсим содержимое плейсхолдера
        node = _parse_placeholder_content(context)
        
        # Пропускаем пробелы перед закрывающей скобкой
        _skip_whitespace(context)
        
        # Потребляем }
        context.consume(DynamicTokenType("PLACEHOLDER_END"))
        
        # Успешно распарсили, убираем сохраненную позицию
        context.discard_saved_position()
        return node
        
    except ParserError:
        # Откатываемся при ошибке
        context.restore_position()
        return None
    except Exception:
        # Откатываемся при любой другой ошибке
        context.restore_position()
        return None


def _parse_placeholder_content(context: ParsingContext) -> TemplateNode:
    """
    Парсит содержимое плейсхолдера после ${.
    
    Определяет тип плейсхолдера и создает соответствующий узел.
    """
    # Проверяем, есть ли tpl: или ctx: в начале
    if _check_include_prefix(context):
        return _parse_include_placeholder(context)
    
    # Проверяем адресную ссылку @origin:name
    if context.match(DynamicTokenType("AT")):
        return _parse_addressed_section(context)
    
    # Обычная секция
    return _parse_simple_section(context)


def _check_include_prefix(context: ParsingContext) -> bool:
    """Проверяет, начинается ли плейсхолдер с tpl: или ctx: (включая адресные формы tpl@origin:name)."""
    current = context.current()
    if current.type != DynamicTokenType("IDENTIFIER"):
        return False
    
    # Проверяем, что идентификатор - это tpl или ctx
    if current.value not in ["tpl", "ctx"]:
        return False
    
    # Проверяем следующий токен после идентификатора
    next_token = context.peek(1)
    # Допускаем как : (локальные ссылки tpl:name), так и @ (адресные ссылки tpl@origin:name)
    return next_token.type in (DynamicTokenType("COLON"), DynamicTokenType("AT"))


def _parse_include_placeholder(context: ParsingContext) -> IncludeNode:
    """
    Парсит плейсхолдер включения tpl:name или ctx:name.
    
    Поддерживает адресные формы:
    - tpl@origin:name
    - tpl@[origin]:name
    """
    # Получаем тип включения
    kind_token = context.consume(DynamicTokenType("IDENTIFIER"))
    kind = kind_token.value
    
    if kind not in ["tpl", "ctx"]:
        raise ParserError(f"Expected 'tpl' or 'ctx', got '{kind}'", kind_token)
    
    # Проверяем на адресную ссылку
    if context.match(DynamicTokenType("AT")):
        # Адресная форма: tpl@origin:name или tpl@[origin]:name
        context.advance()  # потребляем @
        origin, name = _parse_addressed_reference(context)
        return IncludeNode(kind=kind, name=name, origin=origin)
    
    # Обычная форма: tpl:name
    context.consume(DynamicTokenType("COLON"))
    name = _parse_identifier_path(context)
    
    return IncludeNode(kind=kind, name=name, origin="self")


def _parse_addressed_section(context: ParsingContext) -> SectionNode:
    """
    Парсит адресную ссылку на секцию @origin:name.
    """
    context.consume(DynamicTokenType("AT"))  # потребляем @
    origin, name = _parse_addressed_reference(context)
    
    # Создаем SectionNode с адресной ссылкой
    # resolved_ref будет заполнен резолвером
    return SectionNode(section_name=f"@{origin}:{name}")


def _parse_simple_section(context: ParsingContext) -> SectionNode:
    """
    Парсит простую ссылку на секцию section_name.
    """
    name = _parse_identifier_path(context)
    return SectionNode(section_name=name)


def _parse_addressed_reference(context: ParsingContext) -> tuple[str, str]:
    """
    Парсит адресную ссылку origin:name или [origin]:name.
    
    Returns:
        Кортеж (origin, name)
    """
    # Проверяем скобочную форму [origin]:name
    if context.match(DynamicTokenType("LBRACKET")):
        context.advance()  # потребляем [
        
        # Парсим origin внутри скобок (может содержать :)
        origin_parts = []
        while not context.match(DynamicTokenType("RBRACKET")) and not context.is_at_end():
            token = context.advance()
            origin_parts.append(token.value)
        
        if context.is_at_end():
            raise ParserError("Expected ']' to close bracketed origin", context.current())
            
        context.consume(DynamicTokenType("RBRACKET"))  # потребляем ]
        context.consume(DynamicTokenType("COLON"))     # потребляем :
        
        origin = "".join(origin_parts)
        name = _parse_identifier_path(context)
        
        return origin, name
    
    # Обычная форма origin:name
    origin = _parse_identifier_path(context)
    context.consume(DynamicTokenType("COLON"))
    name = _parse_identifier_path(context)
    
    return origin, name


def _parse_identifier_path(context: ParsingContext) -> str:
    """
    Парсит путь-идентификатор, который может состоять из нескольких частей.
    
    Например: docs/api или simple-name
    """
    parts = []
    
    if not context.match(DynamicTokenType("IDENTIFIER")):
        raise ParserError("Expected identifier", context.current())
    
    # Первая часть
    parts.append(context.advance().value)
    
    # Дополнительные части через / (для путей типа docs/api)
    while (context.match(DynamicTokenType("IDENTIFIER")) and 
           "/" in context.current().value):
        # Если идентификатор содержит слеш, он уже включает путь
        token = context.advance()
        # Заменяем первую часть полным путем
        parts[-1] = token.value
        break
    
    return "".join(parts)


def _skip_whitespace(context: ParsingContext) -> None:
    """Пропускает пробельные символы."""
    while context.match(DynamicTokenType("WHITESPACE")):
        context.advance()


def get_placeholder_parser_rules() -> List[ParsingRule]:
    """
    Возвращает правила парсинга для плейсхолдеров.
    """
    return [
        ParsingRule(
            name="parse_placeholder",
            priority=PluginPriority.PLACEHOLDER,
            parser_func=parse_placeholder
        )
    ]


__all__ = ["get_placeholder_parser_rules"]