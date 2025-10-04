"""
Резолвер ссылок для базовых плейсхолдеров секций и шаблонов.

Портирован из lg.template.resolver для обработки адресных ссылок
и загрузки включаемых шаблонов из других lg-cfg скоупов.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, cast

from .nodes import SectionNode, IncludeNode
from ..common import (
    resolve_cfg_root,
    load_template_from, load_context_from
)
from ..handlers import TemplateProcessorHandlers
from ..nodes import TemplateNode, TemplateAST
from ..protocols import TemplateRegistryProtocol
from ...run_context import RunContext
from ...types import SectionRef


@dataclass(frozen=True)
class ResolvedInclude:
    """Результат резолвинга включения с загруженным и распарсенным AST."""
    kind: str  # "tpl" | "ctx"
    name: str
    origin: str
    cfg_root: Path
    ast: TemplateAST


class CommonPlaceholdersResolver:
    """
    Резолвер ссылок для базовых плейсхолдеров.
    
    Обрабатывает адресные ссылки, загружает включаемые шаблоны
    и заполняет метаданные узлов для последующей обработки.
    """
    
    def __init__(
            self,
            run_ctx: RunContext,
            handlers: TemplateProcessorHandlers,
            registry: TemplateRegistryProtocol,
    ):
        """
        Инициализирует резолвер.
        
        Args:
            run_ctx: Контекст выполнения с настройками и путями
            handlers: Типизированные обработчики для парсинга шаблонов
            registry: Реестр компонентов для парсинга
        """
        self.run_ctx = run_ctx
        self.handlers: TemplateProcessorHandlers = handlers
        self.registry = registry
        self.repo_root = run_ctx.root
        self.current_cfg_root = run_ctx.root / "lg-cfg"
        
        # Стек origin'ов для поддержки вложенных включений (как в V1)
        self._origin_stack: List[str] = ["self"]
        
        # Кэш резолвленных включений
        self._resolved_includes: Dict[str, ResolvedInclude] = {}
        self._resolution_stack: List[str] = []

    def resolve_node(self, node: TemplateNode, context: str = "") -> TemplateNode:
        """
        Резолвит узел базового плейсхолдера (SectionNode или IncludeNode).
        
        Публичный метод для использования процессором.
        """
        if isinstance(node, SectionNode):
            return self._resolve_section_node(node, context)
        elif isinstance(node, IncludeNode):
            return self._resolve_include_node(node, context)
        else:
            # Не наш узел - возвращаем как есть
            return node

    def _resolve_section_node(self, node: SectionNode, context: str = "") -> SectionNode:
        """
        Резолвит секционный узел, обрабатывая адресные ссылки.
        
        Поддерживает форматы:
        - "section_name" → текущий скоуп (использует стек origin как в старом резолвере)
        - "@origin:section_name" → указанный скоуп
        - "@[origin]:section_name" → скоуп с двоеточиями в имени
        """
        section_name = node.section_name
        
        try:
            # Всегда используем _parse_section_reference (как в старом резолвере)
            cfg_root, resolved_name = self._parse_section_reference(section_name)
            
            # Создаем SectionRef для использования в остальной части пайплайна
            scope_dir = cfg_root.parent.resolve()
            try:
                scope_rel = scope_dir.relative_to(self.repo_root.resolve()).as_posix()
                if scope_rel == ".":
                    scope_rel = ""
            except ValueError:
                raise RuntimeError(f"Scope directory outside repository: {scope_dir}")
            
            section_ref = SectionRef(
                name=resolved_name,
                scope_rel=scope_rel, 
                scope_dir=scope_dir
            )
            
            return SectionNode(section_name=resolved_name, resolved_ref=section_ref)
            
        except Exception as e:
            raise RuntimeError(f"Failed to resolve section '{section_name}': {e}")

    def _resolve_include_node(self, node: IncludeNode, context: str = "") -> IncludeNode:
        """
        Резолвит узел включения, загружает и парсит включаемый шаблон.
        """
        # Создаем ключ кэша
        cache_key = node.canon_key()
        
        # Проверяем циклические зависимости
        if cache_key in self._resolution_stack:
            cycle_info = " -> ".join(self._resolution_stack + [cache_key])
            raise RuntimeError(f"Circular include dependency: {cycle_info}")
        
        # Проверяем кэш (как в V1)
        if cache_key in self._resolved_includes:
            resolved_include = self._resolved_includes[cache_key]
            return IncludeNode(
                kind=node.kind,
                name=node.name,
                origin=node.origin,
                children=resolved_include.ast
            )
        
        # Резолвим включение
        self._resolution_stack.append(cache_key)
        try:
            resolved_include = self._load_and_parse_include(node, context)
            self._resolved_includes[cache_key] = resolved_include
            
            return IncludeNode(
                kind=node.kind,
                name=node.name,
                origin=node.origin,
                children=resolved_include.ast
            )
        finally:
            self._resolution_stack.pop()

    def _parse_section_reference(self, section_name: str) -> tuple[Path, str]:
        """
        Парсит ссылку на секцию в различных форматах.
        
        Args:
            section_name: Имя секции (может быть адресным)
            
        Returns:
            Кортеж (cfg_root, resolved_name)
        """
        if section_name.startswith("@["):
            # Скобочная форма: @[origin]:name
            close_bracket = section_name.find("]:")
            if close_bracket < 0:
                raise RuntimeError(f"Invalid section reference format: {section_name}")
            origin = section_name[2:close_bracket]
            name = section_name[close_bracket + 2:]
        elif section_name.startswith("@"):
            # Простая адресная форма: @origin:name
            colon_pos = section_name.find(":", 1)
            if colon_pos < 0:
                raise RuntimeError(f"Invalid section reference format: {section_name}")
            origin = section_name[1:colon_pos]
            name = section_name[colon_pos + 1:]
        else:
            # Простая ссылка без адресности - использует текущий origin из стека (как в V1)
            current_origin = self._origin_stack[-1] if self._origin_stack else "self"
            cfg_root = resolve_cfg_root(
                current_origin,
                current_cfg_root=self.current_cfg_root,
                repo_root=self.repo_root
            )
            return cfg_root, section_name
        
        # Резолвим cfg_root для указанного origin
        cfg_root = resolve_cfg_root(
            origin,
            current_cfg_root=self.current_cfg_root,
            repo_root=self.repo_root
        )
        return cfg_root, name

    def _load_and_parse_include(self, node: IncludeNode, context: str) -> ResolvedInclude:
        """
        Загружает и парсит включаемый шаблон.
        
        Args:
            node: Узел включения для обработки
            context: Контекст для диагностики
            
        Returns:
            Резолвленное включение с AST
        """
        # Резолвим cfg_root
        cfg_root = resolve_cfg_root(
            node.origin,
            current_cfg_root=self.current_cfg_root,
            repo_root=self.repo_root
        )
        
        # Загружаем содержимое
        if node.kind == "ctx":
            _, template_text = load_context_from(cfg_root, node.name)
        elif node.kind == "tpl":
            _, template_text = load_template_from(cfg_root, node.name) 
        else:
            raise RuntimeError(f"Unknown include kind: {node.kind}")
        
        # Парсим шаблон
        from ..parser import parse_template
        from ..registry import TemplateRegistry
        include_ast = parse_template(template_text, registry=cast(TemplateRegistry, self.registry))
        
        # Рекурсивно резолвим включение с новым origin в стеке (как в V1)
        self._origin_stack.append(node.origin)
        try:
            # Ядро применит резолверы всех плагинов, включая наш
            ast: TemplateAST = self.handlers.resolve_ast(include_ast, context)
        finally:
            # Восстанавливаем стек origin после резолвинга
            self._origin_stack.pop()

        return ResolvedInclude(
            kind=node.kind,
            name=node.name,
            origin=node.origin,
            cfg_root=cfg_root,
            ast=ast
        )


__all__ = ["CommonPlaceholdersResolver", "ResolvedInclude"]