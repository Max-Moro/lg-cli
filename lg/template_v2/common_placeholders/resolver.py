"""
Резолвер ссылок для базовых плейсхолдеров секций и шаблонов.

Портирован из lg.template.resolver для обработки адресных ссылок
и загрузки включаемых шаблонов из других lg-cfg скоупов.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from ..nodes import TemplateNode, TemplateAST
from .nodes import SectionNode, IncludeNode
from .common import (
    Locator, parse_locator, resolve_cfg_root,
    load_template_from, load_context_from
)
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
    
    def __init__(self, run_ctx: RunContext, validate_paths: bool = True):
        """
        Инициализирует резолвер.
        
        Args:
            run_ctx: Контекст выполнения с настройками и путями
            validate_paths: Если False, не проверяет существование путей (для тестирования)
        """
        self.run_ctx = run_ctx
        self.repo_root = run_ctx.root
        self.current_cfg_root = run_ctx.root / "lg-cfg"
        self.validate_paths = validate_paths
        
        # Стек origin'ов для отслеживания вложенности включений
        self._origin_stack: List[str] = ["self"]
        
        # Кэш резолвленных включений
        self._resolved_includes: Dict[str, ResolvedInclude] = {}
        self._resolution_stack: List[str] = []

    def resolve_ast(self, ast: TemplateAST, template_name: str = "") -> TemplateAST:
        """
        Резолвит все ссылки в AST шаблона.
        
        Args:
            ast: AST для обработки
            template_name: Имя шаблона для диагностики
            
        Returns:
            AST с резолвленными ссылками
        """
        resolved_nodes = []
        
        for node in ast:
            resolved_node = self._resolve_node(node, template_name)
            resolved_nodes.append(resolved_node)
        
        return resolved_nodes

    def _resolve_node(self, node: TemplateNode, context: str = "") -> TemplateNode:
        """Резолвит один узел AST."""
        if isinstance(node, SectionNode):
            return self._resolve_section_node(node, context)
        elif isinstance(node, IncludeNode):
            return self._resolve_include_node(node, context)
        else:
            # Для других типов узлов возвращаем как есть
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
        
        # Проверяем адресную ссылку
        if section_name.startswith("@"):
            cfg_root, resolved_name = self._parse_section_reference(section_name)
            
            # Создаем SectionRef
            if cfg_root == self.current_cfg_root:
                scope_rel = ""
                scope_dir = self.repo_root
            else:
                # Вычисляем относительный путь скоупа
                scope_dir = cfg_root.parent
                try:
                    scope_rel = scope_dir.relative_to(self.repo_root).as_posix()
                except ValueError:
                    raise RuntimeError(f"Scope directory outside repository: {scope_dir}")
            
            section_ref = SectionRef(
                name=resolved_name,
                scope_rel=scope_rel, 
                scope_dir=scope_dir
            )
            
            return SectionNode(section_name=section_name, resolved_ref=section_ref)
        else:
            # Локальная секция
            section_ref = SectionRef(
                name=section_name,
                scope_rel="",
                scope_dir=self.repo_root
            )
            
            return SectionNode(section_name=section_name, resolved_ref=section_ref)

    def _resolve_include_node(self, node: IncludeNode, context: str = "") -> IncludeNode:
        """
        Резолвит узел включения, загружает и парсит включаемый шаблон.
        """
        # Загружаем и парсим включение
        resolved_include = self._load_and_parse_include(node, context)
        
        # Возвращаем узел с загруженным содержимым
        return IncludeNode(
            kind=node.kind,
            name=node.name,
            origin=node.origin,
            children=resolved_include.ast
        )

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
            # Не адресная ссылка
            return self.current_cfg_root, section_name
        
        # Резолвим cfg_root для указанного origin
        cfg_root = self._resolve_cfg_root_safe(origin)
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
        # Создаем ключ кэша
        cache_key = node.canon_key()
        
        # Проверяем кэш
        if cache_key in self._resolved_includes:
            return self._resolved_includes[cache_key]
        
        # Проверяем циклические зависимости
        if cache_key in self._resolution_stack:
            cycle_info = " -> ".join(self._resolution_stack + [cache_key])
            raise RuntimeError(f"Circular include dependency: {cycle_info}")
        
        self._resolution_stack.append(cache_key)
        
        try:
            # Резолвим cfg_root
            cfg_root = self._resolve_cfg_root_safe(node.origin)
            
            # Загружаем содержимое
            if node.kind == "ctx":
                _, template_text = load_context_from(cfg_root, node.name)
            elif node.kind == "tpl":
                _, template_text = load_template_from(cfg_root, node.name) 
            else:
                raise RuntimeError(f"Unknown include kind: {node.kind}")
            
            # Парсим загруженный шаблон через основной парсер
            # Получаем обработчики через глобальный контекст (временное решение)
            # В идеале резолвер должен получать парсер извне
            from ..nodes import TextNode
            
            # TODO: Интегрировать с основным парсером
            # Пока используем простую заглушку, в реальности нужно:
            # ast = self.template_parser.parse(template_text)
            ast: TemplateAST = [TextNode(text=template_text)]
            
            resolved_include = ResolvedInclude(
                kind=node.kind,
                name=node.name,
                origin=node.origin,
                cfg_root=cfg_root,
                ast=ast
            )
            
            # Кэшируем результат
            self._resolved_includes[cache_key] = resolved_include
            
            return resolved_include
            
        finally:
            # Убираем из стека разрешения
            self._resolution_stack.pop()

    def _resolve_cfg_root_safe(self, origin: str) -> Path:
        """
        Безопасное резолвинг cfg_root с поддержкой тестового режима.
        
        Args:
            origin: Origin для резолвинга ('self' или имя директории)
            
        Returns:
            Путь к lg-cfg директории
        """
        if not self.validate_paths:
            # В тестовом режиме возвращаем фиктивный путь
            if origin == "self":
                return self.current_cfg_root
            else:
                return self.repo_root / origin / "lg-cfg"
        
        return resolve_cfg_root(
            origin,
            current_cfg_root=self.current_cfg_root,
            repo_root=self.repo_root
        )


__all__ = ["CommonPlaceholdersResolver", "ResolvedInclude"]