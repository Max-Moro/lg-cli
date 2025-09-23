"""
AST-узлы для движка шаблонизации.

Определяет иерархию неизменяемых классов узлов для представления
структуры шаблонов с поддержкой условий, режимов и включений.
"""

from __future__ import annotations

from dataclasses import dataclass, field
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
class MarkdownFileNode(TemplateNode):
    """
    Плейсхолдер для прямого включения Markdown-файла ${md:path}.
    
    Представляет ссылку на Markdown-документ, который должен быть
    загружен и обработан через виртуальную секцию с автоматической
    настройкой уровней заголовков.
    """
    path: str                      # Путь к документу относительно скоупа
    origin: str = "self"           # Скоуп (self или путь к области)
    heading_level: Optional[int] = None    # Желаемый уровень заголовка
    strip_h1: Optional[bool] = None        # Флаг удаления H1
    section_id: str = ""           # ID динамически созданной секции
    
    # Метаданные для резолвинга (заполняются во время обработки)
    virtual_section: Optional[SectionRef] = None
    
    def canon_key(self) -> str:
        """
        Возвращает канонический ключ для кэширования и дедупликации.
        """
        params = []
        if self.heading_level is not None:
            params.append(f"level:{self.heading_level}")
        if self.strip_h1 is not None:
            params.append(f"strip_h1:{str(self.strip_h1).lower()}")
        
        param_str = f",{','.join(params)}" if params else ""
        
        if self.origin and self.origin != "self":
            return f"md@{self.origin}:{self.path}{param_str}"
        else:
            return f"md:{self.path}{param_str}"


@dataclass(frozen=True)
class ConditionalBlockNode(TemplateNode):
    """
    Условный блок {% if condition %}...{% elif condition %}...{% else %}...{% endif %}.
    
    Представляет условную конструкцию, которая включает или исключает
    содержимое на основе вычисления условного выражения с поддержкой 
    цепочек elif блоков.
    """
    condition_text: str  # Исходный текст условия
    body: List[TemplateNode]
    elif_blocks: List[ElifBlockNode] = field(default_factory=list)
    else_block: Optional[ElseBlockNode] = None
    
    # AST условия после парсинга (заполняется парсером условий)
    condition_ast: Optional[Condition] = None
    # Результат вычисления (заполняется во время оценки)
    evaluated: Optional[bool] = None


@dataclass(frozen=True)
class ElifBlockNode(TemplateNode):
    """
    Блок {% elif condition %} внутри условных конструкций.
    
    Представляет условное альтернативное содержимое, которое проверяется
    если предыдущие условия в цепочке if/elif не выполнились.
    """
    condition_text: str  # Исходный текст условия
    body: List[TemplateNode]
    
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

def _visit_ast_nodes(ast: TemplateAST, visitor_func) -> None:
    """
    Обобщенная функция для обхода всех узлов в AST.
    
    Args:
        ast: AST для обхода
        visitor_func: Функция, вызываемая для каждого узла
    """
    def _visit_node(node: TemplateNode) -> None:
        visitor_func(node)
        
        # Рекурсивно обходим дочерние узлы
        if isinstance(node, ConditionalBlockNode):
            for child in node.body:
                _visit_node(child)
            for elif_block in node.elif_blocks:
                _visit_node(elif_block)
            if node.else_block:
                _visit_node(node.else_block)
        elif isinstance(node, (ElifBlockNode, ElseBlockNode, ModeBlockNode)):
            for child in node.body:
                _visit_node(child)
        elif isinstance(node, IncludeNode) and node.children:
            for child in node.children:
                _visit_node(child)
    
    for node in ast:
        _visit_node(node)


def collect_section_nodes(ast: TemplateAST) -> List[SectionNode]:
    """
    Собирает все узлы секций из AST (включая вложенные).
    
    Используется для предварительного анализа зависимостей шаблона.
    """
    sections: List[SectionNode] = []
    
    def collect_section(node: TemplateNode) -> None:
        if isinstance(node, SectionNode):
            sections.append(node)
    
    _visit_ast_nodes(ast, collect_section)
    return sections


def collect_include_nodes(ast: TemplateAST) -> List[IncludeNode]:
    """
    Собирает все узлы включений из AST (включая вложенные).
    
    Используется для предварительной загрузки зависимых шаблонов.
    """
    includes: List[IncludeNode] = []
    
    def collect_include(node: TemplateNode) -> None:
        if isinstance(node, IncludeNode):
            includes.append(node)
    
    _visit_ast_nodes(ast, collect_include)
    return includes


def collect_markdown_file_nodes(ast: TemplateAST) -> List[MarkdownFileNode]:
    """
    Собирает все узлы Markdown-файлов из AST (включая вложенные).
    
    Используется для предварительного создания виртуальных секций.
    """
    markdown_files: List[MarkdownFileNode] = []
    
    def collect_markdown_file(node: TemplateNode) -> None:
        if isinstance(node, MarkdownFileNode):
            markdown_files.append(node)
    
    _visit_ast_nodes(ast, collect_markdown_file)
    return markdown_files


def has_conditional_content(ast: TemplateAST) -> bool:
    """
    Проверяет, содержит ли AST условное содержимое.
    
    Возвращает True, если в шаблоне есть условные блоки или блоки режимов.
    """
    found_conditional = False
    
    def check_conditional(node: TemplateNode) -> None:
        nonlocal found_conditional
        if isinstance(node, (ConditionalBlockNode, ElifBlockNode, ModeBlockNode)):
            found_conditional = True
    
    _visit_ast_nodes(ast, check_conditional)
    return found_conditional


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
            for i, elif_block in enumerate(node.elif_blocks):
                lines.append(f"{prefix}  elif[{i}]:")
                lines.append(format_ast_tree([elif_block], indent + 2))
            if node.else_block:
                lines.append(f"{prefix}  else:")
                lines.append(format_ast_tree(node.else_block.body, indent + 2))
        elif isinstance(node, ElifBlockNode):
            lines.append(f"{prefix}ElifBlockNode(condition='{node.condition_text}')")
            if node.body:
                lines.append(f"{prefix}  body:")
                lines.append(format_ast_tree(node.body, indent + 2))
        elif isinstance(node, ModeBlockNode):
            lines.append(f"{prefix}ModeBlockNode(modeset='{node.modeset}', mode='{node.mode}')")
            if node.body:
                lines.append(f"{prefix}  body:")
                lines.append(format_ast_tree(node.body, indent + 2))
        elif isinstance(node, IncludeNode):
            lines.append(f"{prefix}IncludeNode(kind='{node.kind}', name='{node.name}', origin='{node.origin}')")
        elif isinstance(node, MarkdownFileNode):
            lines.append(f"{prefix}MarkdownFileNode(path='{node.path}', origin='{node.origin}', level={node.heading_level}, strip_h1={node.strip_h1})")
        else:
            lines.append(f"{prefix}{type(node).__name__}")
    
    return "\n".join(lines)