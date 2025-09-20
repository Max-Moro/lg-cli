"""
Резолвер ссылок для движка шаблонизации LG V2.

Выполняет отдельную фазу резолвинга между парсингом и оценкой AST,
обрабатывая адресные ссылки на секции и включения из других lg-cfg скоупов.
Адаптирует проверенную логику из старого lg/context/common.py и resolver.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

from .nodes import (
    TemplateAST, TemplateNode, SectionNode, IncludeNode,
    ConditionalBlockNode, ModeBlockNode, ElseBlockNode
)
from .parser import parse_template
from .common import parse_locator, resolve_cfg_root
from ..run_context import RunContext
from ..types import SectionRef


class ResolverError(Exception):
    """Ошибка резолвинга ссылок в шаблоне."""
    
    def __init__(self, message: str, node_info: str = ""):
        super().__init__(f"Resolver error{f' in {node_info}' if node_info else ''}: {message}")
        self.node_info = node_info


@dataclass(frozen=True)
class ResolvedInclude:
    """Результат резолвинга включения с загруженным и распарсенным AST."""
    kind: str  # "tpl" | "ctx"
    name: str
    origin: str
    cfg_root: Path
    ast: TemplateAST


class TemplateResolver:
    """
    Резолвер ссылок для шаблонов LG V2.
    
    Обрабатывает адресные ссылки, загружает включаемые шаблоны
    и заполняет метаданные узлов для последующей обработки.
    """
    
    def __init__(self, run_ctx: RunContext, validate_paths: bool = True, 
                 load_template_fn=None, load_context_fn=None):
        """
        Инициализирует резолвер.
        
        Args:
            run_ctx: Контекст выполнения с настройками и путями
            validate_paths: Если False, не проверяет существование путей (для тестирования)
            load_template_fn: Функция загрузки шаблонов (для тестирования)
            load_context_fn: Функция загрузки контекста (для тестирования)
        """
        self.run_ctx = run_ctx
        self.repo_root = run_ctx.root
        self.current_cfg_root = run_ctx.root / "lg-cfg"
        self.validate_paths = validate_paths
        
        # Функции загрузки (можно переопределить для тестирования)
        if load_template_fn is not None:
            self.load_template_fn = load_template_fn
        else:
            from lg.template.common import load_template_from
            self.load_template_fn = load_template_from
            
        if load_context_fn is not None:
            self.load_context_fn = load_context_fn  
        else:
            from lg.template.common import load_context_from
            self.load_context_fn = load_context_from
        
        # Кэш загруженных шаблонов для предотвращения циклов и повторной загрузки
        self._resolved_includes: Dict[str, ResolvedInclude] = {}
        self._resolution_stack: List[str] = []
        
    def _resolve_cfg_root_safe(self, origin: str) -> Path:
        """
        Безопасное резолвинг cfg_root с поддержкой тестового режима.
        
        Args:
            origin: Origin для резолвинга ('self' или имя директории)
            
        Returns:
            Путь к lg-cfg директории
        """
        if self.validate_paths:
            # Продуктивный режим - используем оригинальную функцию
            return resolve_cfg_root(
                origin, 
                current_cfg_root=self.current_cfg_root, 
                repo_root=self.repo_root
            )
        else:
            # Тестовый режим - не проверяем существование файлов
            if origin == "self":
                return self.current_cfg_root
            else:
                return (self.repo_root / origin / "lg-cfg").resolve()
    
    def resolve_template_references(self, ast: TemplateAST, template_name: str = "") -> TemplateAST:
        """
        Резолвит все ссылки в AST шаблона.
        
        Args:
            ast: AST для обработки
            template_name: Имя шаблона для диагностики
            
        Returns:
            AST с резолвленными ссылками
            
        Raises:
            ResolverError: При ошибке резолвинга ссылок
        """
        try:
            return self._resolve_ast_recursive(ast, template_name)
        except Exception as e:
            if isinstance(e, ResolverError):
                raise
            raise ResolverError(f"Unexpected error during resolution: {e}", template_name)
    
    def _resolve_ast_recursive(self, ast: TemplateAST, context: str = "") -> TemplateAST:
        """Рекурсивно резолвит все узлы в AST."""
        resolved_nodes = []
        
        for node in ast:
            resolved_node = self._resolve_node(node, context)
            resolved_nodes.append(resolved_node)
        
        return resolved_nodes
    
    def _resolve_node(self, node: TemplateNode, context: str = "") -> TemplateNode:
        """Резолвит один узел AST."""
        
        if isinstance(node, SectionNode):
            return self._resolve_section_node(node, context)
        
        elif isinstance(node, IncludeNode):
            return self._resolve_include_node(node, context)
        
        elif isinstance(node, ConditionalBlockNode):
            # Рекурсивно обрабатываем тело условного блока
            resolved_body = self._resolve_ast_recursive(node.body, f"{context}/if")
            resolved_else = None
            if node.else_block:
                resolved_else_body = self._resolve_ast_recursive(node.else_block.body, f"{context}/else")
                resolved_else = ElseBlockNode(body=resolved_else_body)
            
            return ConditionalBlockNode(
                condition_text=node.condition_text,
                body=resolved_body,
                else_block=resolved_else,
                condition_ast=node.condition_ast,
                evaluated=node.evaluated
            )
        
        elif isinstance(node, ModeBlockNode):
            # Рекурсивно обрабатываем тело режимного блока
            resolved_body = self._resolve_ast_recursive(node.body, f"{context}/mode[{node.modeset}:{node.mode}]")
            
            return ModeBlockNode(
                modeset=node.modeset,
                mode=node.mode,
                body=resolved_body,
                original_mode_options=node.original_mode_options,
                original_active_tags=node.original_active_tags,
                original_active_modes=node.original_active_modes
            )
        
        else:
            # Остальные узлы (TextNode, CommentNode, ElseBlockNode) возвращаем как есть
            return node
    
    def _resolve_section_node(self, node: SectionNode, context: str = "") -> SectionNode:
        """
        Резолвит секционный узел, обрабатывая адресные ссылки.
        
        Поддерживает форматы:
        - "section_name" → текущий скоуп
        - "@origin:section_name" → указанный скоуп
        - "@[origin]:section_name" → скоуп с двоеточиями в имени
        """
        section_name = node.section_name
        
        try:
            cfg_root, resolved_name = self._parse_section_reference(section_name)
            
            # Создаем SectionRef для использования в остальной части пайплайна
            scope_dir = cfg_root.parent.resolve()
            scope_rel = scope_dir.relative_to(self.repo_root.resolve()).as_posix()
            if scope_rel == ".":
                scope_rel = ""
            
            resolved_ref = SectionRef(
                name=resolved_name,
                scope_rel=scope_rel,
                scope_dir=scope_dir
            )
            
            return SectionNode(
                section_name=resolved_name,
                resolved_ref=resolved_ref
            )
            
        except Exception as e:
            raise ResolverError(f"Failed to resolve section '{section_name}': {e}", context)
    
    def _resolve_include_node(self, node: IncludeNode, context: str = "") -> IncludeNode:
        """
        Резолвит узел включения, загружает и парсит включаемый шаблон.
        
        Поддерживает форматы:
        - "tpl:name", "ctx:name" → текущий скоуп  
        - "tpl@origin:name", "ctx@origin:name" → указанный скоуп
        - "tpl@[origin]:name", "ctx@[origin]:name" → скоуп с двоеточиями в имени
        """
        include_key = node.canon_key()
        
        try:
            # Проверяем циклы включений
            if include_key in self._resolution_stack:
                cycle_path = " → ".join(self._resolution_stack + [include_key])
                raise ResolverError(f"Circular include detected: {cycle_path}", context)
            
            # Проверяем кэш
            if include_key in self._resolved_includes:
                resolved_include = self._resolved_includes[include_key]
                return IncludeNode(
                    kind=node.kind,
                    name=node.name,
                    origin=node.origin,
                    children=resolved_include.ast
                )
            
            # Резолвим включение
            self._resolution_stack.append(include_key)
            try:
                resolved_include = self._load_and_parse_include(node, context)
                self._resolved_includes[include_key] = resolved_include
                
                return IncludeNode(
                    kind=node.kind,
                    name=node.name,
                    origin=node.origin,
                    children=resolved_include.ast
                )
            finally:
                self._resolution_stack.pop()
                
        except Exception as e:
            if isinstance(e, ResolverError):
                raise
            raise ResolverError(f"Failed to resolve include '{node.canon_key()}': {e}", context)
    
    def _parse_section_reference(self, section_name: str) -> Tuple[Path, str]:
        """
        Парсит ссылку на секцию в различных форматах.
        
        Args:
            section_name: Имя секции (может быть адресным)
            
        Returns:
            Кортеж (cfg_root, resolved_name)
        """
        if section_name.startswith("@["):
            # @[origin]:name
            close = section_name.find("]:")
            if close < 0:
                raise ValueError(f"Invalid section reference (missing ']:' ): {section_name}")
            origin = section_name[2:close]
            name = section_name[close + 2:]
            cfg_root = self._resolve_cfg_root_safe(origin)
            return cfg_root, name
        elif section_name.startswith("@"):
            # @origin:name
            colon = section_name.find(":")
            if colon < 0:
                raise ValueError(f"Invalid section reference (missing ':'): {section_name}")
            origin = section_name[1:colon]
            name = section_name[colon + 1:]
            cfg_root = self._resolve_cfg_root_safe(origin)
            return cfg_root, name
        else:
            # Простая ссылка без адресности
            return self.current_cfg_root, section_name
    
    def _load_and_parse_include(self, node: IncludeNode, context: str) -> ResolvedInclude:
        """
        Загружает и парсит включаемый шаблон.
        
        Args:
            node: Узел включения для обработки
            context: Контекст для диагностики
            
        Returns:
            Резолвленное включение с AST
        """
        include_spec = node.canon_key()
        
        # Парсим адресную ссылку
        try:
            locator = parse_locator(include_spec, expected_kind=node.kind)
        except Exception as e:
            raise ResolverError(f"Invalid include format '{include_spec}': {e}", context)
        
        # Резолвим cfg_root
        try:
            cfg_root = self._resolve_cfg_root_safe(locator.origin)
        except Exception as e:
            raise ResolverError(f"Failed to resolve cfg_root for origin '{locator.origin}': {e}", context)
        
        # Загружаем шаблон
        try:
            if node.kind == "tpl":
                _, template_text = self.load_template_fn(cfg_root, locator.resource)
            elif node.kind == "ctx":
                _, template_text = self.load_context_fn(cfg_root, locator.resource)
            else:
                raise ValueError(f"Unknown include kind: {node.kind}")
        except Exception as e:
            raise ResolverError(f"Failed to load {node.kind} '{locator.resource}' from {cfg_root}: {e}", context)
        
        # Парсим шаблон
        try:
            include_ast = parse_template(template_text)
        except Exception as e:
            raise ResolverError(f"Failed to parse {node.kind} '{locator.resource}': {e}", context)
        
        # Рекурсивно резолвим включение
        include_context = f"{context}/{node.kind}:{locator.resource}"
        resolved_ast = self._resolve_ast_recursive(include_ast, include_context)
        
        return ResolvedInclude(
            kind=node.kind,
            name=locator.resource,
            origin=locator.origin,
            cfg_root=cfg_root,
            ast=resolved_ast
        )


__all__ = ["TemplateResolver", "ResolverError"]