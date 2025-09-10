"""
Система анализа видимости элементов кода для языковых адаптеров.
Унифицирует логику определения публичности, приватности и экспортируемости элементов.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import List, Tuple, Optional

from .tree_sitter_support import Node, TreeSitterDocument


class Visibility(Enum):
    """Уровни видимости элементов кода."""
    PUBLIC = "public"           # Публичный элемент
    PROTECTED = "protected"     # Защищенный элемент  
    PRIVATE = "private"         # Приватный элемент
    INTERNAL = "internal"       # Внутренний элемент (для некоторых языков)


class ExportStatus(Enum):
    """Статусы экспорта элементов."""
    EXPORTED = "exported"       # Элемент экспортируется
    NOT_EXPORTED = "not_exported"  # Элемент не экспортируется
    UNKNOWN = "unknown"         # Статус экспорта неизвестен


@dataclass(frozen=True)
class ElementVisibility:
    """Полная информация о видимости элемента кода."""
    visibility: Visibility      # Уровень видимости (public/private/protected)
    export_status: ExportStatus # Статус экспорта
    is_method: bool            # Является ли элемент методом класса
    element_type: str          # Тип элемента (function, method, class, etc.)
    
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
        """
        Должен ли элемент быть включен в публичное API.
        
        Правила:
        - Методы: включаются если публичные
        - Top-level элементы: включаются если экспортируются
        """
        if self.is_method:
            return self.is_public
        else:
            return self.is_exported


@dataclass(frozen=True)  
class PrivateElement:
    """Информация о приватном элементе для удаления."""
    node: Node
    element_type: str          # Тип для плейсхолдеров (function, method, class, etc.)
    visibility_info: ElementVisibility


class VisibilityAnalyzer(ABC):
    """
    Абстрактный анализатор видимости элементов кода.
    Каждый языковой адаптер должен предоставить свою реализацию.
    """
    
    def __init__(self, doc: TreeSitterDocument):
        self.doc = doc
    
    # ============= Основной API =============
    
    def analyze_element_visibility(self, node: Node) -> ElementVisibility:
        """
        Анализирует видимость элемента кода.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Полная информация о видимости элемента
        """
        visibility = self.determine_visibility(node)
        export_status = self.determine_export_status(node)
        is_method = self.is_method_element(node)
        element_type = self.get_element_type(node)
        
        return ElementVisibility(
            visibility=visibility,
            export_status=export_status,
            is_method=is_method,
            element_type=element_type
        )
    
    def collect_all_private_elements(self, context) -> List[PrivateElement]:
        """
        Собирает все приватные элементы для удаления в режиме public API.
        
        Args:
            context: Контекст обработки
            
        Returns:
            Список приватных элементов для удаления
        """
        private_elements = []
        
        # Собираем универсальные элементы (функции, методы, классы)
        universal_elements = self._collect_universal_elements(context)
        private_elements.extend(universal_elements)
        
        # Собираем язык-специфичные элементы
        language_specific_elements = self._collect_language_specific_elements(context)
        private_elements.extend(language_specific_elements)
        
        return private_elements
    
    # ============= Абстрактные методы для реализации в подклассах =============
    
    @abstractmethod
    def determine_visibility(self, node: Node) -> Visibility:
        """
        Определяет уровень видимости элемента.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Уровень видимости элемента
        """
        pass
    
    @abstractmethod
    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Определяет статус экспорта элемента.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Статус экспорта элемента
        """
        pass
    
    @abstractmethod
    def is_method_element(self, node: Node) -> bool:
        """
        Определяет, является ли элемент методом класса.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            True если элемент является методом класса
        """
        pass
    
    @abstractmethod
    def get_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента для использования в плейсхолдерах.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Строка с типом элемента (function, method, class, interface, etc.)
        """
        pass
    
    @abstractmethod
    def _collect_language_specific_elements(self, context) -> List[PrivateElement]:
        """
        Собирает язык-специфичные приватные элементы.
        
        Args:
            context: Контекст обработки
            
        Returns:
            Список язык-специфичных приватных элементов
        """
        pass
    
    # ============= Универсальные методы =============
    
    def _collect_universal_elements(self, context) -> List[PrivateElement]:
        """
        Собирает универсальные элементы (функции, методы, классы).
        
        Args:
            context: Контекст обработки
            
        Returns:
            Список универсальных приватных элементов
        """
        private_elements = []
        
        # Анализируем функции и методы
        functions = context.doc.query("functions")
        for node, capture_name in functions:
            if capture_name in ("function_definition", "function_name"):
                if capture_name == "function_name":
                    # Получаем узел определения функции
                    func_def = node.parent
                else:
                    func_def = node
                
                if func_def:
                    visibility_info = self.analyze_element_visibility(func_def)
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=func_def,
                            element_type=visibility_info.element_type,
                            visibility_info=visibility_info
                        ))
        
        # Анализируем классы
        classes = context.doc.query("classes")
        for node, capture_name in classes:
            if capture_name == "class_name":
                class_def = node.parent
                if class_def:
                    visibility_info = self.analyze_element_visibility(class_def)
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=class_def,
                            element_type="class",
                            visibility_info=visibility_info
                        ))
        
        return private_elements
    
    # ============= Утилиты =============
    
    def get_element_name(self, node: Node) -> Optional[str]:
        """
        Извлекает имя элемента из узла Tree-sitter.
        Базовая реализация, может быть переопределена в подклассах.
        """
        # Ищем дочерний узел с именем функции/класса/метода
        for child in node.children:
            if child.type == "identifier":
                return self.doc.get_node_text(child)
        
        # Для некоторых типов узлов имя может быть в поле name
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)
        
        return None
