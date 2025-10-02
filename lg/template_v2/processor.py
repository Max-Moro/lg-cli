"""
Основной процессор для модульного шаблонизатора.

Оркестрирующий компонент, предоставляющий тот же API что и старый шаблонизатор,
но использующий модульную архитектуру с плагинами.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from .base import ProcessingError
from .handlers import DefaultTemplateProcessorHandlers, TemplateProcessorHandlers
from .lexer import ModularLexer
from .nodes import TemplateNode, TemplateAST, TextNode
from .parser import ModularParser
from .registry import TemplateRegistry
from ..run_context import RunContext
# Импортируем только разрешенные компоненты для совместимости
from ..template.context import TemplateContext
from ..template.processor import TemplateProcessingError
from ..types import SectionRef

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """
    Основной процессор шаблонов для модульной версии.
    
    Предоставляет тот же интерфейс что и lg.template.processor.TemplateProcessor,
    но использует модульную архитектуру с плагинами.
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
        self.lexer = ModularLexer(self.registry)
        self.parser = ModularParser(self.registry)
        
        # Кэши для производительности
        self._template_cache: Dict[str, TemplateAST] = {}
        
        # Внутренние обработчики для плагинов
        self.handlers = DefaultTemplateProcessorHandlers()
        
        # Обработчик секций (устанавливается извне)
        self.section_handler: Optional[Callable[[SectionRef, TemplateContext], str]] = None

    def get_registry(self) -> TemplateRegistry:
        """Возвращает реестр для регистрации плагинов."""
        return self.registry

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
    
    def get_template_dependencies(self, template_name: str) -> Dict[str, Any]:
        """
        Анализирует зависимости шаблона.
        
        Args:
            template_name: Имя шаблона для анализа
            
        Returns:
            Словарь зависимостей
        """
        def analyze_dependencies():
            template_text = self._load_template_text(template_name)
            ast = self._parse_template(template_text, template_name)
            
            # Базовая заглушка - в реальности будет делегировать плагинам
            return {
                "sections": [],
                "includes": [],
                "conditional": False
            }
        
        return self._handle_template_errors(
            analyze_dependencies,
            template_name,
            "Failed to analyze dependencies"
        )
    
    def prevalidate_template(self, template_name: str) -> List[str]:
        """
        Предварительная валидация шаблона.
        
        Args:
            template_name: Имя шаблона для валидации
            
        Returns:
            Список найденных проблем (пустой если проблем нет)
        """
        issues = []
        
        try:
            template_text = self._load_template_text(template_name)
            ast = self._parse_template(template_text, template_name)
            # Валидация будет выполняться плагинами
        except Exception as e:
            issues.append(f"Failed to parse template: {e}")
        
        return issues
    
    # Внутренние методы

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
        try:
            # Получаем обработчики для данного типа узла
            processors = self.registry.get_processors_for_node(type(node))
            
            if processors:
                # Используем первый (наивысший приоритет) обработчик
                processor_rule = processors[0]
                return processor_rule.processor_func(node)
            
            # Fallback для базовых узлов
            if isinstance(node, TextNode):
                return node.text
            
            # Неизвестный тип узла - возвращаем заглушку
            logger.warning(f"No processor found for node type: {type(node).__name__}")
            return f"[{type(node).__name__}]"
            
        except Exception as e:
            node_info = f"{type(node).__name__} at index {node_index}"
            raise ProcessingError(f"Failed to process node: {e}", node, node_info)

    def _load_template_text(self, template_name: str) -> str:
        """Загружает текст шаблона из файла."""
        try:
            # Попытка загрузить как контекст
            from .common_placeholders.common import load_context_from
            _, text = load_context_from(self.run_ctx.root / "lg-cfg", template_name)
            return text
        except FileNotFoundError:
            try:
                # Попытка загрузить как шаблон
                from .common_placeholders.common import load_template_from
                _, text = load_template_from(self.run_ctx.root / "lg-cfg", template_name)
                return text
            except FileNotFoundError:
                raise TemplateProcessingError(f"Template not found: {template_name}")

    def _resolve_template_references(self, ast: TemplateAST, template_name: str = "") -> TemplateAST:
        """
        Резолвит все ссылки в AST с использованием резолвера плагинов.

        Args:
            ast: AST для резолвинга
            template_name: Имя шаблона для диагностики

        Returns:
            AST с резолвленными ссылками
        """
        try:
            # Создаем резолвер для базовых плейсхолдеров
            from .common_placeholders.resolver import CommonPlaceholdersResolver
            
            resolver = CommonPlaceholdersResolver(self.run_ctx)
            return resolver.resolve_ast(ast, template_name)
            
        except Exception as e:
            raise TemplateProcessingError(f"Failed to resolve template references: {e}", template_name, e)

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


def create_v2_template_processor(run_ctx: RunContext) -> TemplateProcessor:
    """
    Создает процессор шаблонов версии 2 с уже установленными доступными плагинами.
    
    Args:
        run_ctx: Контекст выполнения
        
    Returns:
        Настроенный процессор шаблонов
    """
    # Создаем новый реестр для этого процессора
    registry = TemplateRegistry()
    
    # Регистрируем доступные плагины
    from .common_placeholders import CommonPlaceholdersPlugin
    registry.register_plugin(CommonPlaceholdersPlugin())
    
    # Создаем процессор
    processor = TemplateProcessor(run_ctx, registry)
    
    # Настраиваем типизированные обработчики
    _setup_processor_handlers(processor)
    
    # Регистрируем процессоры плагинов после установки обработчиков
    registry.register_plugin_processors(processor.handlers)
    
    return processor


def _setup_processor_handlers(processor: TemplateProcessor) -> None:
    """
    Настраивает типизированные обработчики процессора.
    
    Args:
        processor: Процессор для настройки
    """
    # Настраиваем обработчик узлов AST
    def ast_processor(node: TemplateNode) -> str:
        return processor._evaluate_node(node, [], 0)
    
    processor.handlers.set_ast_processor(ast_processor)
    
    # Настраиваем обработчик секций (будет установлен позже через set_section_handler)
    def section_processor(section_ref: SectionRef) -> str:
        if processor.section_handler is None:
            raise RuntimeError(f"No section handler set for processing section '{section_ref.name}'")
        return processor.section_handler(section_ref, processor.template_ctx)
    
    processor.handlers.set_section_processor(section_processor)
    
    # Настраиваем парсер шаблонов для включений
    def template_parser(template_text: str, template_name: str) -> str:
        # Парсим и обрабатываем включаемый шаблон с правильным именем
        ast = processor._parse_template(template_text, template_name)
        resolved_ast = processor._resolve_template_references(ast, template_name)
        return processor._evaluate_ast(resolved_ast)
    
    processor.handlers.set_template_parser(template_parser)


__all__ = ["TemplateProcessor", "TemplateProcessingError", "create_v2_template_processor"]