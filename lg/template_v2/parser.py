"""
Модульный синтаксический анализатор для шаблонизатора.

Использует правила парсинга из зарегистрированных плагинов для построения AST.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .base import ParsingContext, ParsingRule
from .registry import TemplateRegistry, get_registry
from ..template.lexer import Token, TokenType
from ..template.nodes import TemplateNode, TemplateAST, TextNode

logger = logging.getLogger(__name__)


class ModularParser:
    """
    Синтаксический анализатор, использующий правила из плагинов.
    
    Применяет зарегистрированные в TemplateRegistry правила парсинга
    в порядке приоритета для создания AST.
    """
    
    def __init__(self, registry: Optional[TemplateRegistry] = None):
        """
        Инициализирует парсер с указанным реестром.
        
        Args:
            registry: Реестр компонентов (по умолчанию - глобальный)
        """
        self.registry = registry or get_registry()
        
        # Получаем правила парсинга, отсортированные по приоритету
        self.parser_rules: List[ParsingRule] = []
        self._initialize_rules()
    
    def _initialize_rules(self) -> None:
        """Инициализирует правила парсинга из реестра."""
        self.parser_rules = self.registry.get_sorted_parser_rules()
        logger.debug(f"Initialized parser with {len(self.parser_rules)} rules")
    
    def parse(self, tokens: List[Token]) -> TemplateAST:
        """
        Парсит токены в AST с использованием зарегистрированных правил.
        
        Args:
            tokens: Список токенов для парсинга
            
        Returns:
            AST шаблона
            
        Raises:
            ParserError: При ошибке синтаксического анализа
        """
        context = ParsingContext(tokens)
        ast: List[TemplateNode] = []
        
        while not context.is_at_end():
            node = self._parse_next_node(context)
            if node:
                ast.append(node)
            else:
                # Если ни одно правило не сработало, пытаемся обработать как текст
                self._handle_unparsed_token(context, ast)
        
        logger.debug(f"Parsed AST with {len(ast)} nodes")
        return ast
    
    def _parse_next_node(self, context: ParsingContext) -> Optional[TemplateNode]:
        """
        Пытается применить каждое правило парсинга для текущей позиции.
        
        Args:
            context: Контекст парсинга
            
        Returns:
            Узел AST или None если ни одно правило не сработало
        """
        # Сохраняем позицию для возможного отката
        context.save_position()
        
        # Пробуем каждое правило в порядке приоритета
        for rule in self.parser_rules:
            if not rule.enabled:
                continue
                
            try:
                # Восстанавливаем позицию перед каждой попыткой
                context.restore_position()
                context.save_position()
                
                # Применяем правило
                node = rule.parser_func(context)
                if node is not None:
                    # Правило сработало, убираем сохраненную позицию
                    context.discard_saved_position()
                    logger.debug(f"Applied rule '{rule.name}' -> {type(node).__name__}")
                    return node
                    
            except Exception as e:
                # Правило вызвало исключение, продолжаем с других правил
                logger.debug(f"Rule '{rule.name}' failed: {e}")
                continue
        
        # Ни одно правило не сработало, восстанавливаем позицию
        context.restore_position()
        return None
    
    def _handle_unparsed_token(self, context: ParsingContext, ast: List[TemplateNode]) -> None:
        """
        Обрабатывает токен, который не удалось распарсить правилами.
        
        Args:
            context: Контекст парсинга
            ast: Текущий AST для добавления узла
        """
        current_token = context.current()
        
        if current_token.type == TokenType.TEXT:
            # Обычный текст - создаем TextNode
            text_value = current_token.value
            context.advance()
            
            # Объединяем с предыдущим TextNode если возможно
            if ast and isinstance(ast[-1], TextNode):
                ast[-1] = TextNode(text=ast[-1].text + text_value)
            else:
                ast.append(TextNode(text=text_value))
                
        else:
            # Неожиданный токен - создаем ошибку или обрабатываем как текст
            logger.warning(f"Unexpected token: {current_token.type.name} at {current_token.line}:{current_token.column}")
            
            # Обрабатываем как текст
            text_value = current_token.value
            context.advance()
            
            if ast and isinstance(ast[-1], TextNode):
                ast[-1] = TextNode(text=ast[-1].text + text_value)
            else:
                ast.append(TextNode(text=text_value))


def create_default_parser() -> ModularParser:
    """
    Создает парсер с базовыми правилами для совместимости.
    
    Returns:
        Настроенный модульный парсер
    """
    from .base import ParsingRule, PluginPriority
    from ..template.lexer import TokenType
    
    registry = get_registry()
    
    # Добавляем базовое правило для текста, если нет других правил
    if not registry.parser_rules:
        def parse_text(context: ParsingContext) -> Optional[TemplateNode]:
            """Базовое правило для парсинга текстовых токенов."""
            if context.current().type == TokenType.TEXT:
                token = context.advance()
                return TextNode(text=token.value)
            return None
        
        text_rule = ParsingRule(
            name="parse_text",
            priority=PluginPriority.TEXT,
            parser_func=parse_text
        )
        
        registry.parser_rules["parse_text"] = text_rule
    
    return ModularParser(registry)


__all__ = ["ModularParser", "create_default_parser"]