"""
Процессор шаблонов для движка шаблонизации.

Публичный API, объединяющий все компоненты движка шаблонизации
в удобный интерфейс для обработки шаблонов с поддержкой условий,
режимов и включений.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Callable, Any

from .common import load_template_from, load_context_from
from .context import TemplateContext
from .evaluator import TemplateEvaluationError
from .lexer import LexerError
from .nodes import (
    TemplateAST, TemplateNode, TextNode, SectionNode, IncludeNode,
    ConditionalBlockNode, ModeBlockNode, CommentNode, MarkdownFileNode,
    collect_section_nodes, collect_include_nodes, has_conditional_content
)
from .parser import ParserError, parse_template
from .resolver import TemplateResolver, ResolverError
from .virtual_sections import VirtualSectionFactory
from ..run_context import RunContext
from ..types import SectionRef


class TemplateProcessingError(Exception):
    """Общая ошибка обработки шаблона."""
    
    def __init__(self, message: str, template_name: str = "", cause: Optional[Exception] = None):
        super().__init__(f"Template processing error in '{template_name}': {message}")
        self.template_name = template_name
        self.cause = cause


class TemplateProcessor:
    """
    Основной процессор шаблонов.
    
    Координирует работу всех компонентов движка шаблонизации:
    лексера, парсера, оценщика условий и рендерера.
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
        
        # Резолвер для обработки адресных ссылок
        self.resolver = TemplateResolver(
            run_ctx, 
            validate_paths=validate_paths,
            load_template_fn=self._load_template_from_wrapper,
            load_context_fn=self._load_context_from_wrapper
        )
        
        # Фабрика для создания виртуальных секций
        self.virtual_factory = VirtualSectionFactory()
        
        # Кэш загруженных и обработанных шаблонов
        self._template_cache: Dict[str, TemplateAST] = {}
        self._resolved_cache: Dict[str, TemplateAST] = {}
        
        # Хендлеры для обработки различных типов узлов
        self.section_handler: Optional[Callable[[SectionRef, TemplateContext], str]] = None

    def _load_template_from_wrapper(self, cfg_root, name):
        """Обёртка для load_template_from, которую можно мокать в тестах."""
        return load_template_from(cfg_root, name)

    def _load_context_from_wrapper(self, cfg_root, name):
        """Обёртка для load_context_from, которую можно мокать в тестах."""
        return load_context_from(cfg_root, name)

    def set_section_handler(self, handler: Callable[[SectionRef, TemplateContext], str]) -> None:
        """
        Устанавливает обработчик секций.
        
        Args:
            handler: Функция для обработки плейсхолдеров секций
                    Принимает (section_name, template_context) -> rendered_text
        """
        self.section_handler = handler
    
    def _handle_template_errors(self, func, template_name: str, error_message: str):
        """
        Общий обработчик ошибок для операций с шаблонами.
        
        Args:
            func: Функция для выполнения
            template_name: Имя шаблона для диагностики
            error_message: Сообщение об ошибке
        """
        try:
            return func()
        except (LexerError, ParserError, ResolverError, TemplateEvaluationError) as e:
            raise TemplateProcessingError(str(e), template_name, e)
        except TemplateProcessingError:
            # Повторный бросок без дополнительной обёртки
            raise
        except Exception as e:
            raise TemplateProcessingError(f"{error_message}: {e}", template_name, e)
    
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
            # Определяем тип и загружаем шаблон
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
            # 1. Парсим шаблон
            ast = self._parse_template(template_text, template_name)
            
            # 2. Резолвим ссылки (адресные секции и включения)
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
            Словарь зависимостей: 
            {
                "sections": [список имен секций],
                "includes": [список включаемых шаблонов],
                "conditional": True/False - есть ли условное содержимое
            }
        """
        def analyze_dependencies():
            template_text = self._load_template_text(template_name)
            ast = self._parse_template(template_text, template_name)
            
            # Собираем зависимости
            section_nodes = collect_section_nodes(ast)
            include_nodes = collect_include_nodes(ast)
            
            return {
                "sections": [node.section_name for node in section_nodes],
                "includes": [f"{node.canon_key()}" for node in include_nodes],
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
            
            # Проверяем корректность условий
            issues.extend(self._validate_conditions(ast))
            
            # Проверяем доступность включаемых шаблонов
            issues.extend(self._validate_includes(ast))
            
        except Exception as e:
            issues.append(f"Failed to parse template: {e}")
        
        return issues
    
    # Внутренние методы

    def _resolve_template_references(self, ast: TemplateAST, template_name: str = "") -> TemplateAST:
        """
        Резолвит все ссылки в AST с использованием TemplateResolver.

        Args:
            ast: AST для резолвинга
            template_name: Имя шаблона для диагностики

        Returns:
            AST с резолвленными ссылками

        Raises:
            TemplateProcessingError: При ошибке резолвинга
        """
        try:
            return self.resolver.resolve_template_references(ast, template_name)
        except ResolverError as e:
            raise TemplateProcessingError(f"Resolution failed: {e}", template_name, e)
        except Exception as e:
            raise TemplateProcessingError(f"Unexpected error during resolution: {e}", template_name, e)
    
    def _parse_template(self, template_text: str, template_name: str) -> TemplateAST:
        """Парсит текст шаблона в AST с кэшированием."""
        cache_key = f"{template_name}:{hash(template_text)}"
        
        if cache_key not in self._template_cache:
            ast = parse_template(template_text)
            self._template_cache[cache_key] = ast
        
        return self._template_cache[cache_key]
    
    def _evaluate_ast(self, ast: TemplateAST) -> str:
        """Оценивает AST и возвращает отрендеренный текст."""
        result_parts = []
        
        for node in ast:
            result_parts.append(self._evaluate_node(node))
        
        return "".join(result_parts)
    
    def _evaluate_node(self, node: TemplateNode) -> str:
        """Оценивает один узел AST."""
        if isinstance(node, TextNode):
            return node.text
        
        elif isinstance(node, SectionNode):
            if self.section_handler and node.resolved_ref:
                return self.section_handler(node.resolved_ref, self.template_ctx)
            else:
                # Если нет обработчика секций, возвращаем плейсхолдер
                return f"${{section:{node.section_name}}}"
        
        elif isinstance(node, IncludeNode):
            if node.children:
                # Входим в скоуп включаемого шаблона
                self.template_ctx.enter_include_scope(node.origin)
                try:
                    result = self._evaluate_ast(node.children)
                finally:
                    # Всегда выходим из скоупа, даже при ошибке
                    self.template_ctx.exit_include_scope()
                return result
            else:
                # Если включение не резолвлено, возвращаем плейсхолдер  
                return f"${{{node.canon_key()}}}"
        
        elif isinstance(node, ConditionalBlockNode):
            # Оцениваем основное условие
            should_include = self.template_ctx.evaluate_condition(node.condition_ast)
            
            if should_include:
                return self._evaluate_ast(node.body)
            
            # Проверяем elif блоки по порядку
            for elif_block in node.elif_blocks:
                elif_should_include = self.template_ctx.evaluate_condition(elif_block.condition_ast)
                if elif_should_include:
                    return self._evaluate_ast(elif_block.body)
            
            # Если ни одно условие не выполнилось, проверяем else блок
            if node.else_block:
                return self._evaluate_ast(node.else_block.body)
            else:
                return ""
        
        elif isinstance(node, ModeBlockNode):
            # Входим в режимный блок
            self.template_ctx.enter_mode_block(node.modeset, node.mode)
            try:
                result = self._evaluate_ast(node.body)
            finally:
                # Всегда выходим из блока, даже при ошибке
                self.template_ctx.exit_mode_block()
            
            return result
        
        elif isinstance(node, MarkdownFileNode):
            # Проверяем условие включения если оно задано
            if node.condition:
                try:
                    should_include = self.template_ctx.evaluate_condition_text(node.condition)
                    if not should_include:
                        # Условие не выполнено - пропускаем узел
                        return ""
                except Exception as e:
                    # Ошибка при вычислении условия - возвращаем комментарий об ошибке
                    return f"<!-- Error evaluating condition '{node.condition}': {e} -->"
            
            # Обрабатываем Markdown-файл через виртуальную секцию
            if self.section_handler:
                # Создаем конфигурацию для виртуальной секции
                try:
                    section_config, section_ref = self.virtual_factory.create_for_markdown_file(
                        node=node,
                        repo_root=self.run_ctx.root
                    )
                    
                    # Устанавливаем виртуальную секцию в контекст
                    self.template_ctx.set_virtual_section(section_config)
                    
                    try:
                        # Обрабатываем через section_handler
                        result = self.section_handler(section_ref, self.template_ctx)
                    finally:
                        # Всегда очищаем виртуальную секцию после обработки
                        self.template_ctx.clear_virtual_section()
                    
                    return result
                    
                except Exception as e:
                    # В случае ошибки очищаем контекст и возвращаем плейсхолдер
                    self.template_ctx.clear_virtual_section()
                    return f"<!-- Error processing {node.canon_key()}: {e} -->"
            else:
                # Если виртуальная секция не создана или нет обработчика, возвращаем плейсхолдер
                return f"${{{node.canon_key()}}}"
        
        elif isinstance(node, CommentNode):
            # Комментарии игнорируются
            return ""
        
        else:
            # Неизвестный тип узла
            return f"<!-- Unknown node type: {type(node).__name__} -->"
    
    def _load_template_text(self, template_name: str, kind: str = "ctx") -> str:
        """Загружает текст шаблона из файла."""
        cfg_root = self.run_ctx.root / "lg-cfg"
        
        if kind == "tpl":
            _, text = load_template_from(cfg_root, template_name)
        else:  # kind == "ctx"
            _, text = load_context_from(cfg_root, template_name)
        
        return text
    
    def _validate_conditions(self, ast: TemplateAST) -> List[str]:
        """Валидирует все условия в AST."""
        issues = []
        
        def check_node(node: TemplateNode) -> None:
            if isinstance(node, ConditionalBlockNode):
                try:
                    self.template_ctx.evaluate_condition(node.condition_ast)
                except Exception as e:
                    issues.append(f"Invalid condition '{node.condition_text}': {e}")
                
                # Рекурсивно проверяем тело
                for child in node.body:
                    check_node(child)
                
                if node.else_block:
                    for child in node.else_block.body:
                        check_node(child)
            
            elif isinstance(node, ModeBlockNode):
                # Проверяем доступность режима
                try:
                    modes_config = self.template_ctx.adaptive_loader.get_modes_config()
                    if node.modeset not in modes_config.mode_sets:
                        issues.append(f"Unknown mode set '{node.modeset}'")
                    elif node.mode not in modes_config.mode_sets[node.modeset].modes:
                        issues.append(f"Unknown mode '{node.mode}' in mode set '{node.modeset}'")
                except Exception as e:
                    issues.append(f"Error validating mode {node.modeset}:{node.mode}: {e}")
                
                # Рекурсивно проверяем тело
                for child in node.body:
                    check_node(child)
        
        for node in ast:
            check_node(node)
        
        return issues
    
    def _validate_includes(self, ast: TemplateAST) -> List[str]:
        """Валидирует доступность всех включений в AST."""
        issues = []
        
        include_nodes = collect_include_nodes(ast)
        for node in include_nodes:
            try:
                self._load_template_text(node.name, node.kind)
            except Exception as e:
                issues.append(f"Cannot load {node.canon_key()}: {e}")
        
        return issues
