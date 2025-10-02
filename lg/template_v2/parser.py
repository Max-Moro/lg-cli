"""
Модульный синтаксический анализатор для шаблонизатора.

Использует правила парсинга из зарегистрированных плагинов для построения AST.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from .base import ParsingContext, ParsingRule
from .nodes import TemplateNode, TemplateAST, TextNode
from .registry import TemplateRegistry
from .tokens import Token, TokenType

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
        self.registry = registry
        
        # Получаем правила парсинга, отсортированные по приоритету
        self.parser_rules: List[ParsingRule] = []
        self._initialize_rules()
    
    def _initialize_rules(self) -> None:
        """Инициализирует правила парсинга из реестра."""
        if self.registry is None:
            raise RuntimeError("Registry is required for parser initialization")
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


def parse_template(text: str, registry: Optional[TemplateRegistry] = None) -> TemplateAST:
    """
    Удобная функция для парсинга шаблона из текста.
    
    Args:
        text: Исходный текст шаблона
        registry: Реестр компонентов (если None, создает базовый)
        
    Returns:
        AST шаблона
        
    Raises:
        LexerError: При ошибке лексического анализа 
        ParserError: При ошибке синтаксического анализа
    """
    if registry is None:
        # Создаем минимальный реестр с базовыми плейсхолдерами
        from .registry import TemplateRegistry
        from .common_placeholders import CommonPlaceholdersPlugin
        
        registry = TemplateRegistry()
        registry.register_plugin(CommonPlaceholdersPlugin())
    
    from .lexer import ModularLexer
    
    lexer = ModularLexer(registry)
    tokens = lexer.tokenize(text)
    
    parser = ModularParser(registry)
    return parser.parse(tokens)


__all__ = ["ModularParser", "parse_template"]