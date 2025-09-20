"""
AST-узлы для движка шаблонизации LG V2.

Определяет иерархию неизменяемых классов узлов для представления
структуры шаблонов с поддержкой условий, режимов и включений.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Set, Dict

from ..conditions.model import Condition
from ..config.adaptive_model import ModeOptions
from ..types import SectionRef


@dataclass(frozen=True)
class TemplateNode:
    """Базовый класс для всех узлов AST шаблона."""
    pass


@dataclass(frozen=True)
class TextNode(TemplateNode):
    """
    Обычный текстовый контент в шаблоне.
    
    Представляет статический текст, который не требует обработки
    и выводится в результат как есть.
    """
    text: str


@dataclass(frozen=True)
class SectionNode(TemplateNode):
    """
    Плейсхолдер секции ${section}.
    
    Представляет ссылку на секцию, которая должна быть разрешена
    и заменена на отрендеренное содержимое секции.
    """
    section_name: str
    # Метаданные для резолвинга (заполняются во время парсинга/резолвинга)
    resolved_ref: Optional[SectionRef] = None


@dataclass(frozen=True)
class IncludeNode(TemplateNode):
    """
    Плейсхолдер для включения шаблона ${tpl:name} или ${ctx:name}.
    
    Представляет ссылку на другой шаблон или контекст, который должен
    быть загружен, обработан и включен в текущее место.
    """
    kind: str  # "tpl" или "ctx"
    name: str
    origin: str  # "self" или путь к области (например, "apps/web")
    
    # Для хранения вложенного AST после резолвинга и парсинга
    children: Optional[List[TemplateNode]] = None

    def canon_key(self) -> str:
        """
        Возвращает канонический ключ.
        """
        if self.origin and self.origin != "self":
            return f"{self.kind}@{self.origin}:{self.name}"
        else:
            return f"{self.kind}:{self.name}"


@dataclass(frozen=True)
class ConditionalBlockNode(TemplateNode):
    """
    Условный блок {% if condition %}...{% endif %}.
    
    Представляет условную конструкцию, которая включает или исключает
    содержимое на основе вычисления условного выражения.
    """
    condition_text: str  # Исходный текст условия
    body: List[TemplateNode]
    else_block: Optional[ElseBlockNode] = None
    
    # AST условия после парсинга (заполняется парсером условий)
    condition_ast: Optional[Condition] = None
    # Результат вычисления (заполняется во время оценки)
    evaluated: Optional[bool] = None


@dataclass(frozen=True)
class ElseBlockNode(TemplateNode):
    """
    Блок {% else %} внутри условных конструкций.
    
    Представляет альтернативное содержимое, которое используется
    если условие в ConditionalBlockNode не выполняется.
    """
    body: List[TemplateNode]


@dataclass(frozen=True)
class ModeBlockNode(TemplateNode):
    """
    Блок переопределения режима {% mode modeset:mode %}...{% endmode %}.
    
    Представляет блок, внутри которого активен определенный режим,
    переопределяющий глобальные настройки для обработки вложенного содержимого.
    """
    modeset: str
    mode: str
    body: List[TemplateNode]
    
    # Сохраненное состояние контекста (заполняется во время выполнения)
    original_mode_options: Optional[ModeOptions] = None
    original_active_tags: Optional[Set[str]] = None
    original_active_modes: Optional[Dict[str, str]] = None


@dataclass(frozen=True)
class CommentNode(TemplateNode):
    """
    Блок комментария {# комментарий #}.
    
    Представляет комментарий в шаблоне, который игнорируется 
    при рендеринге и не попадает в итоговый результат.
    """
    text: str


# Тип для коллекции узлов шаблона
TemplateAST = List[TemplateNode]


# Вспомогательные функции для работы с AST

def collect_section_nodes(ast: TemplateAST) -> List[SectionNode]:
    """
    Собирает все узлы секций из AST (включая вложенные).
    
    Используется для предварительного анализа зависимостей шаблона.
    """
    sections: List[SectionNode] = []
    
    def _visit_node(node: TemplateNode) -> None:
        if isinstance(node, SectionNode):
            sections.append(node)
        elif isinstance(node, ConditionalBlockNode):
            for child in node.body:
                _visit_node(child)
            if node.else_block:
                _visit_node(node.else_block)
        elif isinstance(node, ModeBlockNode):
            for child in node.body:
                _visit_node(child)
        elif isinstance(node, ElseBlockNode):
            for child in node.body:
                _visit_node(child)
        elif isinstance(node, IncludeNode) and node.children:
            for child in node.children:
                _visit_node(child)
    
    for node in ast:
        _visit_node(node)
    
    return sections


def collect_include_nodes(ast: TemplateAST) -> List[IncludeNode]:
    """
    Собирает все узлы включений из AST (включая вложенные).
    
    Используется для предварительной загрузки зависимых шаблонов.
    """
    includes: List[IncludeNode] = []
    
    def _visit_node(node: TemplateNode) -> None:
        if isinstance(node, IncludeNode):
            includes.append(node)
            # Также проверяем вложенные узлы после разрешения
            if node.children:
                for child in node.children:
                    _visit_node(child)
        elif isinstance(node, (ConditionalBlockNode, ModeBlockNode)):
            for child in node.body:
                _visit_node(child)
        elif isinstance(node, ElseBlockNode):
            for child in node.body:
                _visit_node(child)
    
    for node in ast:
        _visit_node(node)
    
    return includes


def has_conditional_content(ast: TemplateAST) -> bool:
    """
    Проверяет, содержит ли AST условное содержимое.
    
    Возвращает True, если в шаблоне есть условные блоки или блоки режимов.
    """
    def _check_node(node: TemplateNode) -> bool:
        if isinstance(node, (ConditionalBlockNode, ModeBlockNode)):
            return True
        elif isinstance(node, (ConditionalBlockNode, ModeBlockNode)):
            return any(_check_node(child) for child in node.body)
        elif isinstance(node, ElseBlockNode):
            return any(_check_node(child) for child in node.body)
        elif isinstance(node, IncludeNode) and node.children:
            return any(_check_node(child) for child in node.children)
        return False
    
    return any(_check_node(node) for node in ast)


def format_ast_tree(ast: List[TemplateNode], indent: int = 0) -> str:
    """Format AST as a tree structure for debugging."""
    lines = []
    prefix = "  " * indent
    
    for node in ast:
        if isinstance(node, TextNode):
            lines.append(f"{prefix}TextNode('{node.text}')")
        elif isinstance(node, SectionNode):
            lines.append(f"{prefix}SectionNode('{node.section_name}')")
        elif isinstance(node, CommentNode):
            lines.append(f"{prefix}CommentNode('{node.text}')")
        elif isinstance(node, ConditionalBlockNode):
            lines.append(f"{prefix}ConditionalBlockNode(condition='{node.condition_text}')")
            if node.body:
                lines.append(f"{prefix}  body:")
                lines.append(format_ast_tree(node.body, indent + 2))
            if node.else_block:
                lines.append(f"{prefix}  else:")
                lines.append(format_ast_tree(node.else_block.body, indent + 2))
        elif isinstance(node, ModeBlockNode):
            lines.append(f"{prefix}ModeBlockNode(modeset='{node.modeset}', mode='{node.mode}')")
            if node.body:
                lines.append(f"{prefix}  body:")
                lines.append(format_ast_tree(node.body, indent + 2))
        elif isinstance(node, IncludeNode):
            lines.append(f"{prefix}IncludeNode(kind='{node.kind}', name='{node.name}', origin='{node.origin}')")
        else:
            lines.append(f"{prefix}{type(node).__name__}")
    
    return "\n".join(lines)