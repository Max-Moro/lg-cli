"""
Унифицированная система анализа кода для языковых адаптеров.
Объединяет анализ структуры и видимости в единый компонент без дублирования.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any

from .tree_sitter_support import Node, TreeSitterDocument


# ============= Модели данных =============

class Visibility(Enum):
    """Уровни видимости элементов кода."""
    PUBLIC = "public"
    PROTECTED = "protected"
    PRIVATE = "private"
    INTERNAL = "internal"


class ExportStatus(Enum):
    """Статусы экспорта элементов."""
    EXPORTED = "exported"
    NOT_EXPORTED = "not_exported"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ElementInfo:
    """Полная информация об элементе кода."""
    node: Node
    element_type: str           # "function", "method", "class", "interface", etc.
    name: Optional[str] = None
    visibility: Visibility = Visibility.PUBLIC
    export_status: ExportStatus = ExportStatus.UNKNOWN
    is_method: bool = False
    decorators: List[Node] = None
    
    def __post_init__(self):
        if self.decorators is None:
            object.__setattr__(self, 'decorators', [])
    
    @property
    def is_public(self) -> bool:
        """Является ли элемент публичным."""
        return self.visibility == Visibility.PUBLIC
    
    @property
    def is_private(self) -> bool:
        """Является ли элемент приватным или защищенным."""
        return self.visibility in (Visibility.PRIVATE, Visibility.PROTECTED)
    
    @property
    def is_exported(self) -> bool:
        """Экспортируется ли элемент."""
        return self.export_status == ExportStatus.EXPORTED
    
    @property
    def should_be_included_in_public_api(self) -> bool:
        """Должен ли элемент быть включен в публичное API."""
        if self.is_method:
            return self.is_public
        else:
            return self.is_exported


@dataclass(frozen=True)
class FunctionGroup:
    """Группа узлов, относящихся к одной функции/методу."""
    definition: Node
    element_info: ElementInfo
    name_node: Optional[Node] = None
    body_node: Optional[Node] = None


@dataclass(frozen=True)
class PrivateElement:
    """Информация о приватном элементе для удаления."""
    element_info: ElementInfo
    
    @property
    def node(self) -> Node:
        """Convenience property для доступа к узлу."""
        return self.element_info.node
    
    @property
    def element_type(self) -> str:
        """Convenience property для доступа к типу."""
        return self.element_info.element_type


# ============= Основной анализатор =============

class CodeAnalyzer(ABC):
    """
    Унифицированный анализатор кода.
    Объединяет функциональность анализа структуры и видимости.
    """
    
    def __init__(self, doc: TreeSitterDocument):
        self.doc = doc
    
    # ============= Основной API =============
    
    def analyze_element(self, node: Node) -> ElementInfo:
        """
        Полный анализ элемента кода.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Полная информация об элементе
        """
        element_type = self.determine_element_type(node)
        name = self.extract_element_name(node)
        visibility = self.determine_visibility(node)
        export_status = self.determine_export_status(node)
        is_method = self.is_method_context(node)
        decorators = self.find_decorators_for_element(node)
        
        return ElementInfo(
            node=node,
            element_type=element_type,
            name=name,
            visibility=visibility,
            export_status=export_status,
            is_method=is_method,
            decorators=decorators
        )
    
    def collect_private_elements_for_public_api(self) -> List[PrivateElement]:
        """
        Собирает все приватные элементы для удаления в режиме public API.
        
        Returns:
            Список приватных элементов для удаления
        """
        private_elements = []
        
        # Собираем универсальные элементы

        # TODO Адаптировать старую логику
        # # Find all functions and methods using language-specific structure analysis
        # functions = context.doc.query("functions")
        # private_elements = []  # List of (element_node, element_type)
        #
        # # Group function-like captures using language-specific utilities
        # function_groups = analyzer.collect_function_like_elements(functions)
        #
        # for func_def, func_group in function_groups.items():
        #     element_type = func_group.element_type
        #
        #     # Check element visibility using adapter's language-specific logic
        #     is_public = self.adapter.is_public_element(func_def, context.doc)
        #     is_exported = self.adapter.is_exported_element(func_def, context.doc)
        #
        #     # Universal logic based on element type
        #     should_remove = False
        #
        #     if element_type == "method":
        #         # Method removed if private/protected
        #         should_remove = not is_public
        #     else:  # function, arrow_function, etc.
        #         # Top-level function removed if not exported
        #         should_remove = not is_exported
        #
        #     if should_remove:
        #         private_elements.append((func_def, element_type))
        #
        # # Also check classes
        # classes = context.doc.query("classes")
        # for node, capture_name in classes:
        #     if capture_name == "class_name":
        #         class_def = node.parent
        #         # Check class export status
        #         is_exported = self.adapter.is_exported_element(class_def, context.doc)
        #
        #         # For top-level classes, export is primary consideration
        #         if not is_exported:
        #             private_elements.append((class_def, "class"))


        # Собираем язык-специфичные элементы
        language_specific_elements = self.collect_language_specific_private_elements()
        private_elements.extend(language_specific_elements)
        
        return private_elements
    
    # ============= Структурный анализ =============
    
    def collect_function_like_elements(self, captures: List[Tuple[Node, str]]) -> Dict[Node, FunctionGroup]:
        """
        Группирует захваты Tree-sitter по функциям/методам.
        
        Args:
            captures: Список (node, capture_name) из Tree-sitter запроса
            
        Returns:
            Словарь: function_node -> FunctionGroup с информацией о функции
        """
        function_groups = {}
        
        # Сначала собираем все определения функций
        for node, capture_name in captures:
            if self.is_function_definition_capture(capture_name):
                element_info = self.analyze_element(node)
                function_groups[node] = FunctionGroup(
                    definition=node,
                    element_info=element_info
                )
        
        # Затем ищем соответствующие тела и имена
        for node, capture_name in captures:
            if self.is_function_body_capture(capture_name):
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    old_group = function_groups[func_def]
                    function_groups[func_def] = FunctionGroup(
                        definition=old_group.definition,
                        element_info=old_group.element_info,
                        name_node=old_group.name_node,
                        body_node=node
                    )
            
            elif self.is_function_name_capture(capture_name):
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    old_group = function_groups[func_def]
                    function_groups[func_def] = FunctionGroup(
                        definition=old_group.definition,
                        element_info=old_group.element_info,
                        name_node=node,
                        body_node=old_group.body_node
                    )
        
        # Обрабатываем случаи когда нет явного definition в захватах
        for node, capture_name in captures:
            if self.is_function_name_capture(capture_name) and node not in function_groups:
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def not in function_groups:
                    element_info = self.analyze_element(func_def)
                    function_groups[func_def] = FunctionGroup(
                        definition=func_def,
                        element_info=element_info,
                        name_node=node
                    )
        
        return function_groups

    def find_decorators_for_element(self, node: Node) -> List[Node]:
        """
        Находит все декораторы/аннотации для элемента кода Python.

        Работает в двух режимах:
        1. Если элемент обернут в decorated_definition - извлекает декораторы из него
        2. Иначе ищет декораторы среди предыдущих sibling узлов

        Args:
            node: Узел элемента (функция, класс, метод)

        Returns:
            Список узлов декораторов в порядке их появления в коде
        """
        decorators = []

        # Режим 1: Проверяем parent на decorated_definition
        parent = node.parent
        if parent and parent.type in self.get_decorated_definition_types():
            # Ищем дочерние узлы-декораторы в wrapped definition
            for child in parent.children:
                if child.type in self.get_decorator_types():
                    decorators.append(child)
                elif child == node:
                    # Дошли до самого элемента - прекращаем поиск
                    break

        # Режим 2: Ищем декораторы среди предыдущих sibling узлов
        preceding_decorators = self._find_preceding_decorators(node)

        # Объединяем результаты, избегая дубликатов
        all_decorators = decorators + [d for d in preceding_decorators if d not in decorators]

        return all_decorators

    def get_element_range_with_decorators(self, node: Node) -> Tuple[int, int]:
        """
        Получает диапазон элемента включая его декораторы/аннотации.
        
        Args:
            node: Узел элемента
            
        Returns:
            Tuple (start_byte, end_byte) включая все связанные декораторы
        """
        decorators = self.find_decorators_for_element(node)
        
        if decorators:
            start_byte = min(decorator.start_byte for decorator in decorators)
            end_byte = node.end_byte
            return start_byte, end_byte
        else:
            return self.doc.get_node_range(node)
    
    # ============= Абстрактные методы для реализации в подклассах =============
    
    @abstractmethod
    def determine_element_type(self, node: Node) -> str:
        """Определяет тип элемента."""
        pass
    
    @abstractmethod
    def extract_element_name(self, node: Node) -> Optional[str]:
        """Извлекает имя элемента."""
        pass
    
    @abstractmethod
    def determine_visibility(self, node: Node) -> Visibility:
        """Определяет видимость элемента."""
        pass
    
    @abstractmethod
    def determine_export_status(self, node: Node) -> ExportStatus:
        """Определяет статус экспорта элемента."""
        pass
    
    @abstractmethod
    def is_method_context(self, node: Node) -> bool:
        """Определяет, является ли элемент методом класса."""
        pass
    
    @abstractmethod
    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """Находит определение функции в родительских узлах."""
        pass
    
    @abstractmethod
    def get_decorated_definition_types(self) -> Set[str]:
        """Возвращает типы узлов для wrapped decorated definitions."""
        pass
    
    @abstractmethod
    def get_decorator_types(self) -> Set[str]:
        """Возвращает типы узлов для отдельных декораторов."""
        pass
    
    @abstractmethod
    def collect_language_specific_private_elements(self) -> List[PrivateElement]:
        """Собирает язык-специфичные приватные элементы."""
        pass
    
    # ============= Вспомогательные методы =============
    
    def is_function_definition_capture(self, capture_name: str) -> bool:
        """Проверяет, является ли capture определением функции."""
        return capture_name in ("function_definition", "method_definition")
    
    def is_function_body_capture(self, capture_name: str) -> bool:
        """Проверяет, является ли capture телом функции."""
        return capture_name in ("function_body", "method_body")
    
    def is_function_name_capture(self, capture_name: str) -> bool:
        """Проверяет, является ли capture именем функции."""
        return capture_name in ("function_name", "method_name")
    
    def _find_preceding_decorators(self, node: Node) -> List[Node]:
        """Находит декораторы среди предыдущих sibling узлов."""
        decorators = []
        
        if not node.parent:
            return decorators
        
        siblings = node.parent.children
        node_index = None
        for i, sibling in enumerate(siblings):
            if sibling == node:
                node_index = i
                break
        
        if node_index is None:
            return decorators
        
        for i in range(node_index - 1, -1, -1):
            sibling = siblings[i]
            if sibling.type in self.get_decorator_types():
                decorators.insert(0, sibling)
            elif self._is_whitespace_or_comment(sibling):
                continue
            else:
                break
        
        return decorators
    
    @abstractmethod
    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """Проверяет, является ли узел пробелом или комментарием."""
        pass


# ============= Экспорт =============

__all__ = [
    "CodeAnalyzer",
    "ElementInfo", 
    "FunctionGroup",
    "PrivateElement",
    "Visibility",
    "ExportStatus"
]
