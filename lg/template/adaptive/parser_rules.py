"""
Правила парсинга для адаптивных конструкций в шаблонах.

Обрабатывает директивы {% ... %}, комментарии {# ... #},
условные блоки if-elif-else, режимные блоки mode-endmode.
"""

from __future__ import annotations

from typing import Callable, List, Optional

from .nodes import ConditionalBlockNode, ElifBlockNode, ElseBlockNode, ModeBlockNode, CommentNode
from ..nodes import TemplateNode
from ..tokens import ParserError
from ..types import PluginPriority, ParsingRule, ParsingContext

# Тип функтора для рекурсивного парсинга
ParseNextNodeFunc = Callable[[ParsingContext], Optional[TemplateNode]]


class AdaptiveParserRules:
    """
    Класс правил парсинга для адаптивных конструкций.
    
    Инкапсулирует все правила парсинга с доступом к функтору
    рекурсивного парсинга через состояние экземпляра.
    """
    
    def __init__(self, parse_next_node: ParseNextNodeFunc):
        """
        Инициализирует правила парсинга.
        
        Args:
            parse_next_node: Функтор для рекурсивного парсинга следующего узла
        """
        self.parse_next_node = parse_next_node
    
    def parse_directive(self, context: ParsingContext) -> Optional[TemplateNode]:
        """
        Парсит директиву {% ... %}.
        
        Может быть условием (if), режимом (mode) или их завершением.
        Рекурсивно обрабатывает вложенные директивы.
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
        return self._parse_directive_content(content_tokens, context)


    def _parse_directive_content(self, content_tokens: List, context: ParsingContext) -> TemplateNode:
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
            return self._parse_if_directive(content_tokens, context)
        elif keyword == 'elif':
            raise ParserError("elif without if", first_token)
        elif keyword == 'else':
            # Самостоятельный else не должен встречаться (обрабатывается внутри if)
            raise ParserError("else without if", first_token)
        elif keyword == 'mode':
            return self._parse_mode_directive(content_tokens, context)
        elif keyword == 'endif':
            raise ParserError("endif without if", first_token)
        elif keyword == 'endmode':
            raise ParserError("endmode without mode", first_token)
        else:
            raise ParserError(f"Unknown directive: {first_token.value}", first_token)


    def _parse_if_directive(self, content_tokens: List, context: ParsingContext) -> ConditionalBlockNode:
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
        
        condition_text = self._reconstruct_condition_text(condition_tokens)
        
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
            if self._check_directive_keyword(context, 'endif'):
                self._consume_directive_keyword(context, 'endif')
                found_end = True
                break
            elif self._check_directive_keyword(context, 'elif'):
                # Парсим elif блоки
                elif_blocks.extend(self._parse_elif_blocks(context))
                # После парсинга всех elif блоков проверяем else
                if self._check_directive_keyword(context, 'else'):
                    self._consume_directive_keyword(context, 'else')
                    else_block = self._parse_else_block(context)
                self._consume_directive_keyword(context, 'endif')
                found_end = True
                break
            elif self._check_directive_keyword(context, 'else'):
                self._consume_directive_keyword(context, 'else')
                else_block = self._parse_else_block(context)
                self._consume_directive_keyword(context, 'endif')
                found_end = True
                break
            
            # Парсим следующий узел (рекурсивно применяем все правила парсинга)
            # используем функтор для вызова парсера
            node = self.parse_next_node(context)
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


    def _parse_elif_blocks(self, context: ParsingContext) -> List[ElifBlockNode]:
        """
        Парсит последовательность elif блоков.
        """
        elif_blocks = []
        
        while self._check_directive_keyword(context, 'elif'):
            # Потребляем {%
            context.consume("DIRECTIVE_START")
            
            # Собираем токены содержимого elif директивы
            content_tokens = []
            while not context.is_at_end() and not context.match("DIRECTIVE_END"):
                content_tokens.append(context.advance())
            
            # Потребляем %}
            context.consume("DIRECTIVE_END")
            
            # Парсим содержимое elif директивы
            elif_block = self._parse_single_elif_directive(content_tokens, context)
            elif_blocks.append(elif_block)
        
        return elif_blocks

    def _parse_single_elif_directive(self, content_tokens: List, context: ParsingContext) -> ElifBlockNode:
        """Парсит одну elif директиву из уже извлеченных токенов содержимого."""
        # Пропускаем пробелы в начале
        non_whitespace = [t for t in content_tokens if t.type != "WHITESPACE"]
        if not non_whitespace or non_whitespace[0].value.lower() != 'elif':
            raise ParserError("Expected 'elif' keyword", content_tokens[0] if content_tokens else context.current())
        
        # Находим индекс первого 'elif' токена
        elif_index = -1
        for i, t in enumerate(content_tokens):
            if t.type == "IDENTIFIER" and t.value.lower() == "elif":
                elif_index = i
                break
        
        if elif_index == -1 or elif_index + 1 >= len(content_tokens):
            raise ParserError("Missing condition in elif directive", content_tokens[0])
        
        # Берем все токены после 'elif', исключая пробелы в начале
        condition_tokens = content_tokens[elif_index + 1:]
        while condition_tokens and condition_tokens[0].type == "WHITESPACE":
            condition_tokens = condition_tokens[1:]
        
        if not condition_tokens:
            raise ParserError("Missing condition in elif directive", content_tokens[elif_index])
        
        condition_text = self._reconstruct_condition_text(condition_tokens)
        
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
            if (self._check_directive_keyword(context, 'elif') or 
                self._check_directive_keyword(context, 'else') or 
                self._check_directive_keyword(context, 'endif')):
                break
            
            # Парсим следующий узел - вложенные директивы обрабатываются рекурсивно
            node = self.parse_next_node(context)
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


    def _parse_else_block(self, context: ParsingContext) -> ElseBlockNode:
        """Парсит тело else блока."""
        else_body = []
        
        while not context.is_at_end():
            if self._check_directive_keyword(context, 'endif'):
                break
            
            node = self.parse_next_node(context)
            if node:
                else_body.append(node)
            else:
                # Если не удалось распарсить узел, обрабатываем как текст
                token = context.advance()
                from ..nodes import TextNode
                else_body.append(TextNode(text=token.value))
        
        return ElseBlockNode(body=else_body)

    def _parse_mode_directive(self, content_tokens: List, context: ParsingContext) -> ModeBlockNode:
        """
        Парсит режимную директиву {% mode modeset:mode %}.
        """
        # Ожидаем формат: mode modeset:mode_name
        if len(content_tokens) < 2:
            raise ParserError("Missing mode specification in mode directive", content_tokens[0])
        
        # Находим индекс токена 'mode'
        mode_index = -1
        for i, t in enumerate(content_tokens):
            if t.type == "IDENTIFIER" and t.value.lower() == "mode":
                mode_index = i
                break
        
        if mode_index == -1 or mode_index + 1 >= len(content_tokens):
            raise ParserError("Missing mode specification in mode directive", content_tokens[0])
        
        # Берем все токены после 'mode', исключая пробелы в начале
        mode_spec_tokens = content_tokens[mode_index + 1:]
        while mode_spec_tokens and mode_spec_tokens[0].type == "WHITESPACE":
            mode_spec_tokens = mode_spec_tokens[1:]
        
        if not mode_spec_tokens:
            raise ParserError("Missing mode specification in mode directive", content_tokens[mode_index])
        
        # Собираем спецификацию режима без пробелов
        mode_spec = ''.join(t.value for t in mode_spec_tokens if t.type != "WHITESPACE")
        
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
            if self._check_directive_keyword(context, 'endmode'):
                self._consume_directive_keyword(context, 'endmode')
                found_end = True
                break
            
            node = self.parse_next_node(context)
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


    def parse_comment(self, context: ParsingContext) -> Optional[TemplateNode]:
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

    # Вспомогательные методы

    def _reconstruct_condition_text(self, tokens: List) -> str:
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

    def _check_directive_keyword(self, context: ParsingContext, keyword: str) -> bool:
        """
        Проверяет, является ли следующая конструкция директивой с указанным ключевым словом.
        
        Проверяет последовательность: {% [WHITESPACE] keyword ... %}
        """
        if not context.match("DIRECTIVE_START"):
            return False
        
        # Смотрим вперед, пропуская пробелы
        offset = 1
        while True:
            token = context.peek(offset)
            
            # Достигли конца
            if token.type == "EOF":
                return False
            
            # Нашли непробельный токен
            if token.type != "WHITESPACE":
                # Проверяем, является ли он нужным ключевым словом
                return token.type == "IDENTIFIER" and token.value.lower() == keyword
            
            # Пропускаем пробел
            offset += 1

    def _consume_directive_keyword(self, context: ParsingContext, keyword: str) -> None:
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


def get_adaptive_parser_rules(parse_next_node: ParseNextNodeFunc) -> List[ParsingRule]:
    """
    Возвращает правила парсинга для адаптивных конструкций.
    
    Args:
        parse_next_node: Функтор для рекурсивного парсинга следующего узла
        
    Returns:
        Список правил парсинга с привязанным функтором
    """
    rules_instance = AdaptiveParserRules(parse_next_node)
    
    return [
        ParsingRule(
            name="parse_directive",
            priority=PluginPriority.DIRECTIVE,
            parser_func=rules_instance.parse_directive
        ),
        ParsingRule(
            name="parse_comment",
            priority=PluginPriority.COMMENT,
            parser_func=rules_instance.parse_comment
        )
    ]


__all__ = ["AdaptiveParserRules", "ParseNextNodeFunc", "get_adaptive_parser_rules"]

