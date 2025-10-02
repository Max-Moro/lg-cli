"""
Основной процессор для модульного шаблонизатора.

Оркестрирующий компонент, предоставляющий тот же API что и старый шаблонизатор,
но использующий модульную архитектуру с плагинами.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from .base import ProcessingError
from .registry import TemplateRegistry, get_registry
from .lexer import ModularLexer, create_default_lexer
from .parser import ModularParser, create_default_parser

# Импортируем существующие компоненты для совместимости
from ..template.context import TemplateContext
from ..template.processor import TemplateProcessingError
from ..template.resolver import TemplateResolver
from ..template.virtual_sections import VirtualSectionFactory
from ..template.nodes import TemplateNode, TemplateAST, TextNode
from ..run_context import RunContext
from ..types import SectionRef

logger = logging.getLogger(__name__)


class TemplateProcessor:
    """
    Основной процессор шаблонов для модульной версии.
    
    Предоставляет тот же интерфейс что и lg.template.processor.TemplateProcessor,
    но использует модульную архитектуру с плагинами.
    """
    
    def __init__(self, run_ctx: RunContext, validate_paths: bool = True):
        """
        Инициализирует процессор шаблонов.
        
        Args:
            run_ctx: Контекст выполнения с настройками и сервисами
            validate_paths: Если False, не проверяет существование путей (для тестирования)
        """
        self.run_ctx = run_ctx
        self.template_ctx = TemplateContext(run_ctx)
        
        # Получаем или создаем реестр
        self.registry = get_registry()
        
        # Инициализируем компоненты (будут установлены в _ensure_basic_plugins_registered)
        self.lexer: ModularLexer
        self.parser: ModularParser
        
        # Используем существующие компоненты для совместимости
        self.resolver = TemplateResolver(
            run_ctx, 
            validate_paths=validate_paths,
            load_template_fn=self._load_template_from_wrapper,
            load_context_fn=self._load_context_from_wrapper
        )
        
        self.virtual_factory = VirtualSectionFactory()
        
        # Кэши для производительности
        self._template_cache: Dict[str, TemplateAST] = {}
        self._resolved_cache: Dict[str, TemplateAST] = {}
        
        # Обработчик секций
        self.section_handler: Optional[Callable[[SectionRef, TemplateContext], str]] = None
        
        # Инициализируем базовые плагины если они еще не зарегистрированы
        self._ensure_basic_plugins_registered()

    def _ensure_basic_plugins_registered(self) -> None:
        """Регистрирует базовые плагины если они еще не зарегистрированы."""
        if not self.registry.plugins:
            logger.debug("No plugins registered, using default components")
            # Используем создание по умолчанию, которое добавляет базовые токены/правила
            self.lexer = create_default_lexer()
            self.parser = create_default_parser()
        else:
            # Инициализируем плагины если еще не сделали этого
            if not self.registry.is_initialized():
                self.registry.initialize_plugins()
            
            self.lexer = ModularLexer(self.registry)
            self.parser = ModularParser(self.registry)
        
        # Убеждаемся что компоненты инициализированы
        if self.lexer is None:
            self.lexer = create_default_lexer()
        if self.parser is None:
            self.parser = create_default_parser()

    def _load_template_from_wrapper(self, cfg_root, name):
        """Обёртка для load_template_from, которую можно мокать в тестах."""
        from ..template.common import load_template_from
        return load_template_from(cfg_root, name)

    def _load_context_from_wrapper(self, cfg_root, name):
        """Обёртка для load_context_from, которую можно мокать в тестах."""
        from ..template.common import load_context_from
        return load_context_from(cfg_root, name)

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
            
            # 2. Резолвим ссылки
            resolved_ast = self._resolve_template_references(ast, template_name)
            
            # 3. Обрабатываем AST
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
            
            from ..template.nodes import collect_section_nodes, collect_include_nodes, has_conditional_content
            
            section_nodes = collect_section_nodes(ast)
            include_nodes = collect_include_nodes(ast)
            
            return {
                "sections": [node.section_name for node in section_nodes],
                "includes": [f"{node.kind}:{node.name}" for node in include_nodes],
                "conditional": has_conditional_content(ast)
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
            
            # Проверяем корректность условий (заглушка)
            # issues.extend(self._validate_conditions(ast))
            
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

    def _resolve_template_references(self, ast: TemplateAST, template_name: str = "") -> TemplateAST:
        """Резолвит все ссылки в AST с использованием TemplateResolver."""
        try:
            return self.resolver.resolve_template_references(ast, template_name)
        except Exception as e:
            raise TemplateProcessingError(f"Failed to resolve references: {e}", template_name, e)

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
                return processor_rule.processor_func(node, self.template_ctx)
            
            # Fallback для базовых узлов
            if isinstance(node, TextNode):
                return node.text
            
            # Неизвестный тип узла
            logger.warning(f"No processor found for node type: {type(node).__name__}")
            return ""
            
        except Exception as e:
            node_info = f"{type(node).__name__} at index {node_index}"
            raise ProcessingError(f"Failed to process node: {e}", node, node_info)

    def _load_template_text(self, template_name: str, kind: str = "ctx") -> str:
        """Загружает текст шаблона из файла."""
        try:
            if kind == "ctx":
                _, text = self._load_context_from_wrapper(self.run_ctx.root / "lg-cfg", template_name)
            else:
                _, text = self._load_template_from_wrapper(self.run_ctx.root / "lg-cfg", template_name)
            return text
        except FileNotFoundError:
            # Пробуем другой тип
            if kind == "ctx":
                _, text = self._load_template_from_wrapper(self.run_ctx.root / "lg-cfg", template_name)
            else:
                _, text = self._load_context_from_wrapper(self.run_ctx.root / "lg-cfg", template_name)
            return text

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


__all__ = ["TemplateProcessor", "TemplateProcessingError"]