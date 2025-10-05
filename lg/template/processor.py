"""
Процессор шаблонов для движка шаблонизации.

Публичный API, объединяющий все компоненты движка шаблонизации
в удобный интерфейс для обработки шаблонов с поддержкой условий,
режимов и включений.

Позволяет расширять функционал через плагины.
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

from .context import TemplateContext
from .handlers import TemplateProcessorHandlers
from .lexer import ContextualLexer
from .nodes import TemplateNode, TemplateAST, TextNode
from .parser import ModularParser
from .registry import TemplateRegistry
from .types import ProcessingContext
from ..run_context import RunContext
from ..types import SectionRef

logger = logging.getLogger(__name__)


class TemplateProcessingError(Exception):
    """Общая ошибка обработки шаблона."""

    def __init__(self, message: str, template_name: str = "", cause: Optional[Exception] = None):
        super().__init__(f"Template processing error in '{template_name}': {message}")
        self.template_name = template_name
        self.cause = cause


class TemplateProcessor:
    """
    Основной процессор шаблонов.
    """
    
    def __init__(self, run_ctx: RunContext, registry: TemplateRegistry):
        """
        Инициализирует процессор шаблонов.
        
        Args:
            run_ctx: Контекст выполнения с настройками и сервисами
            registry: Реестр компонентов (передается извне для избежания глобального состояния)
        """
        self.run_ctx = run_ctx
        self.template_ctx = TemplateContext(run_ctx)
        
        # Используем переданный реестр или создаем новый
        self.registry = registry
        
        # Инициализируем компоненты
        self.lexer = ContextualLexer(self.registry)
        self.parser = ModularParser(self.registry)
        
        # Кэши для производительности
        self._template_cache: Dict[str, TemplateAST] = {}
        
        # Обработчик секций (устанавливается извне)
        self.section_handler: Optional[Callable[[SectionRef, TemplateContext], str]] = None
        
        # Создаем анонимный класс обработчиков прямо здесь
        class ProcessorHandlers(TemplateProcessorHandlers):
            def process_ast_node(self, context: ProcessingContext) -> str:
                """Делегирует обработку узла с контекстом."""
                return processor_self._evaluate_node(context.get_node(), context.ast, context.node_index)
            
            def process_section_ref(self, section_ref: SectionRef) -> str:
                if processor_self.section_handler is None:
                    raise RuntimeError(f"No section handler set for processing section '{section_ref.name}'")
                return processor_self.section_handler(section_ref, processor_self.template_ctx)
            
            def parse_next_node(self, context) -> Optional[TemplateNode]:
                """Делегирует парсинг к главному парсеру."""
                return processor_self.parser._parse_next_node(context)
            
            def resolve_ast(self, ast, context: str = "") -> list:
                """Делегирует резолвинг к процессору."""
                return processor_self._resolve_template_references(ast, context)
        
        # Сохраняем ссылку на self для замыкания
        processor_self = self
        self.handlers = ProcessorHandlers()

    def set_section_handler(self, handler: Callable[[SectionRef, TemplateContext], str]) -> None:
        """
        Устанавливает обработчик секций.
        
        Args:
            handler: Функция для обработки плейсхолдеров секций
        """
        self.section_handler = handler
    
    def process_template_file(self, template_name: str) -> str:
        """
        Обрабатывает шаблон из файла lg-cfg/<name>.tpl.md или lg-cfg/<name>.ctx.md.
        
        Args:
            template_name: Имя шаблона (без суффикса .tpl.md/.ctx.md)
            
        Returns:
            Отрендеренный текст шаблона
            
        Raises:
            TemplateProcessingError: При ошибке обработки шаблона
        """
        def process_file():
            template_text = self._load_template_text(template_name)
            return self.process_template_text(template_text, template_name)
        
        return self._handle_template_errors(
            process_file, 
            template_name, 
            "Failed to process template file"
        )
    
    def process_template_text(self, template_text: str, template_name: str = "") -> str:
        """
        Обрабатывает шаблон из текста.
        
        Args:
            template_text: Текст шаблона для обработки
            template_name: Опциональное имя шаблона для диагностики
            
        Returns:
            Отрендеренный текст
            
        Raises:
            TemplateProcessingError: При ошибке обработки шаблона
        """
        def process_text():
            # 1. Парсим шаблон в AST
            ast = self._parse_template(template_text, template_name)
            
            # 2. Резолвим ссылки в AST  
            resolved_ast = self._resolve_template_references(ast, template_name)
            
            # 3. Обрабатываем резолвленный AST
            return self._evaluate_ast(resolved_ast)
        
        return self._handle_template_errors(
            process_text,
            template_name,
            "Unexpected error during processing"
        )

    # ======= Внутренние методы =======

    def _parse_template(self, template_text: str, template_name: str) -> TemplateAST:
        """Парсит текст шаблона в AST с кэшированием."""
        cache_key = f"{template_name}:{hash(template_text)}"
        
        if cache_key not in self._template_cache:
            try:
                tokens = self.lexer.tokenize(template_text)
                ast = self.parser.parse(tokens)
                self._template_cache[cache_key] = ast
                logger.debug(f"Parsed template '{template_name}' -> {len(ast)} nodes")
            except Exception as e:
                raise TemplateProcessingError(f"Failed to parse template: {e}", template_name, e)
        
        return self._template_cache[cache_key]

    def _evaluate_ast(self, ast: TemplateAST) -> str:
        """Оценивает AST и возвращает отрендеренный текст."""
        try:
            result_parts = []
            
            for i, node in enumerate(ast):
                rendered = self._evaluate_node(node, ast, i)
                if rendered:
                    result_parts.append(rendered)
            
            return "".join(result_parts)
        except Exception as e:
            raise TemplateProcessingError(f"Failed to evaluate AST: {e}", cause=e)

    def _evaluate_node(self, node: TemplateNode, ast: TemplateAST, node_index: int) -> str:
        """Оценивает один узел AST."""
        from .types import ProcessingContext
        
        # Создаем контекст обработки
        processing_context = ProcessingContext(ast=ast, node_index=node_index)
        
        # Получаем обработчики для данного типа узла
        processors = self.registry.get_processors_for_node(type(node))

        if processors:
            # Используем первый (наивысший приоритет) обработчик
            processor_rule = processors[0]
            return processor_rule.processor_func(processing_context)

        # Fallback для базовых узлов
        if isinstance(node, TextNode):
            return node.text

        # Неизвестный тип узла - возвращаем заглушку
        logger.warning(f"No processor found for node type: {type(node).__name__}")
        return f"[{type(node).__name__}]"

    def _load_template_text(self, template_name: str) -> str:
        """Загружает текст шаблона из файла."""
        try:
            # Попытка загрузить как контекст
            from .common import load_context_from
            _, text = load_context_from(self.run_ctx.root / "lg-cfg", template_name)
            return text
        except FileNotFoundError:
            try:
                # Попытка загрузить как шаблон
                from .common import load_template_from
                _, text = load_template_from(self.run_ctx.root / "lg-cfg", template_name)
                return text
            except FileNotFoundError:
                raise TemplateProcessingError(f"Template not found: {template_name}")

    def _resolve_template_references(self, ast: TemplateAST, template_name: str = "") -> TemplateAST:
        """
        Резолвит все ссылки в AST рекурсивно через плагины.

        Args:
            ast: AST для резолвинга
            template_name: Имя шаблона для диагностики

        Returns:
            AST с резолвленными ссылками
        """
        try:
            resolved_nodes = []
            for node in ast:
                resolved_node = self._resolve_node(node, template_name)
                resolved_nodes.append(resolved_node)
            return resolved_nodes
        except Exception as e:
            raise TemplateProcessingError(f"Failed to resolve template references: {e}", template_name, e)
    
    def _resolve_node(self, node: TemplateNode, context: str = "") -> TemplateNode:
        """
        Резолвит один узел AST рекурсивно.
        
        Использует резолверы плагинов для специфичных типов узлов,
        автоматически обрабатывает вложенные структуры через рефлексию.
        """
        from dataclasses import fields, replace
        
        # Пытаемся применить специфичные резолверы плагинов
        resolved = self._apply_plugin_resolvers(node, context)
        if resolved is not node:
            # Плагин обработал узел - возвращаем как есть БЕЗ рекурсивной обработки
            # Это важно, так как резолвер плагина уже обработал вложенные узлы
            return resolved

        has_changes = False
        updates = {}
        
        for field in fields(node):
            field_value = getattr(node, field.name)
            
            # Обрабатываем списки узлов
            if isinstance(field_value, list):
                if field_value and all(isinstance(item, TemplateNode) for item in field_value):
                    resolved_list = [self._resolve_node(n, context) for n in field_value]
                    updates[field.name] = resolved_list
                    has_changes = True
                    
            # Обрабатываем одиночные узлы
            elif isinstance(field_value, TemplateNode):
                resolved = self._resolve_node(field_value, context)
                if resolved is not field_value:
                    updates[field.name] = resolved
                    has_changes = True
        
        if has_changes:
            return replace(node, **updates)
        
        return node
    
    def _apply_plugin_resolvers(self, node: TemplateNode, context: str) -> TemplateNode:
        """
        Применяет резолверы плагинов к узлу через registry.
        
        Использует зарегистрированные резолверы для специфичных типов узлов.
        """
        # Получаем резолверы для типа узла
        resolvers = self.registry.get_resolvers_for_node(type(node))
        
        if not resolvers:
            # Нет зарегистрированных резолверов для этого типа
            return node
        
        # Применяем резолвер с наивысшим приоритетом
        resolver_rule = resolvers[0]
        return resolver_rule.resolver_func(node, context)

    def _handle_template_errors(self, func, template_name: str, error_message: str):
        """Общий обработчик ошибок для операций с шаблонами."""
        try:
            return func()
        except TemplateProcessingError:
            # Передаем ошибки обработки как есть
            raise
        except Exception as e:
            # Оборачиваем другие ошибки в TemplateProcessingError
            raise TemplateProcessingError(error_message, template_name, e)


def create_template_processor(run_ctx: RunContext) -> TemplateProcessor:
    """
    Создает процессор шаблонов с уже установленными доступными плагинами.
    
    Args:
        run_ctx: Контекст выполнения
        
    Returns:
        Настроенный процессор шаблонов
    """
    # Создаем новый реестр для этого процессора
    registry = TemplateRegistry()
    
    # Создаем процессор (обработчики настроятся автоматически в конструкторе)
    processor = TemplateProcessor(run_ctx, registry)
    
    # Регистрируем доступные плагины (в порядке приоритета)
    from .common_placeholders import CommonPlaceholdersPlugin
    from .adaptive import AdaptivePlugin
    from .md_placeholders import MdPlaceholdersPlugin
    
    registry.register_plugin(CommonPlaceholdersPlugin(processor.template_ctx))
    registry.register_plugin(AdaptivePlugin(processor.template_ctx))
    registry.register_plugin(MdPlaceholdersPlugin(processor.template_ctx))
    
    # Инициализируем плагины после регистрации всех компонентов
    registry.initialize_plugins(processor.handlers)

    return processor


__all__ = ["TemplateProcessor", "TemplateProcessingError", "create_template_processor"]