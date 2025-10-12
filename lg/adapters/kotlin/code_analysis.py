"""
Kotlin-специфичная реализация унифицированного анализатора кода.
Объединяет функциональность анализа структуры и видимости для Kotlin.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo
from ..tree_sitter_support import Node


class KotlinCodeAnalyzer(CodeAnalyzer):
    """Kotlin-специфичная реализация унифицированного анализатора кода."""

    def determine_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента Kotlin на основе структуры узла.
        
        Args:
            node: Tree-sitter узел
            
        Returns:
            Строка с типом элемента: "function", "method", "class", "object", "property"
        """
        node_type = node.type
        
        if node_type == "class_declaration":
            return "class"
        elif node_type == "object_declaration":
            return "object"
        elif node_type == "function_declaration":
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "property_declaration":
            return "property"
        elif node_type == "secondary_constructor":
            return "constructor"
        else:
            # Fallback: пытаемся определить по родительскому контексту
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Извлекает имя элемента Kotlin из узла Tree-sitter.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Имя элемента или None если не найдено
        """
        # Для property_declaration ищем variable_declaration
        if node.type == "property_declaration":
            for child in node.children:
                if child.type == "variable_declaration":
                    for grandchild in child.children:
                        if grandchild.type == "simple_identifier":
                            return self.doc.get_node_text(grandchild)
        
        # Ищем дочерний узел с именем (simple_identifier или type_identifier)
        for child in node.children:
            if child.type in ("simple_identifier", "type_identifier"):
                return self.doc.get_node_text(child)
        
        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Определяет видимость элемента Kotlin по модификаторам.
        
        Правила Kotlin:
        - private - приватный
        - protected - защищенный
        - internal - внутренний (модуля)
        - public (по умолчанию) - публичный
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Уровень видимости элемента
        """
        # Ищем модификатор видимости среди дочерних узлов
        for child in node.children:
            if child.type == "modifiers":
                for modifier_child in child.children:
                    if modifier_child.type == "visibility_modifier":
                        modifier_text = self.doc.get_node_text(modifier_child)
                        if modifier_text == "private":
                            return Visibility.PRIVATE
                        elif modifier_text == "protected":
                            return Visibility.PROTECTED
                        elif modifier_text == "internal":
                            return Visibility.INTERNAL
                        elif modifier_text == "public":
                            return Visibility.PUBLIC
        
        # В Kotlin по умолчанию все элементы public
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Определяет статус экспорта элемента Kotlin.
        
        Правила:
        - Методы внутри классов/объектов НЕ считаются экспортируемыми напрямую
        - Top-level функции, классы, объекты экспортируются если public/internal
        - private элементы не экспортируются
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Статус экспорта элемента
        """
        # Если это метод/свойство внутри класса, он НЕ экспортируется напрямую
        if node.type == "function_declaration" and self.is_method_context(node):
            return ExportStatus.NOT_EXPORTED
        
        if node.type == "property_declaration" and self.is_inside_class(node):
            return ExportStatus.NOT_EXPORTED
        
        # Для top-level элементов проверяем видимость
        visibility = self.determine_visibility(node)
        
        # В Kotlin public и internal элементы экспортируются
        if visibility in (Visibility.PUBLIC, Visibility.INTERNAL):
            return ExportStatus.EXPORTED
        else:
            return ExportStatus.NOT_EXPORTED

    def is_method_context(self, node: Node) -> bool:
        """
        Определяет, является ли узел методом класса или объекта Kotlin.
        
        Args:
            node: Tree-sitter узел для анализа
            
        Returns:
            True если узел является методом, False если функцией верхнего уровня
        """
        # Проходим вверх по дереву в поисках класса или объекта
        current = node.parent
        while current:
            if current.type in ("class_declaration", "object_declaration", "class_body"):
                return True
            # Останавливаемся на границах файла
            if current.type in ("source_file",):
                break
            current = current.parent
        return False

    def is_inside_class(self, node: Node) -> bool:
        """
        Проверяет, находится ли узел внутри класса или объекта.
        
        Args:
            node: Tree-sitter узел для проверки
            
        Returns:
            True если внутри класса/объекта
        """
        current = node.parent
        while current:
            if current.type in ("class_declaration", "object_declaration"):
                return True
            if current.type == "source_file":
                break
            current = current.parent
        return False

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Находит function_declaration для данного узла, поднимаясь по дереву.
        
        Args:
            node: Узел для поиска родительской функции
            
        Returns:
            Function definition или None если не найден
        """
        current = node.parent
        while current:
            if current.type == "function_declaration":
                return current
            current = current.parent
        return None

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Возвращает типы узлов для wrapped decorated definitions в Kotlin.
        
        В Kotlin аннотации встроены в modifiers, а не оборачивают определения.
        
        Returns:
            Пустое множество (в Kotlin нет wrapped definitions)
        """
        return set()

    def get_decorator_types(self) -> Set[str]:
        """
        Возвращает типы узлов для аннотаций в Kotlin.
        
        Returns:
            Множество типов узлов
        """
        return {
            "annotation",  # Kotlin @Annotation
        }

    def find_decorators_for_element(self, node: Node) -> List[Node]:
        """
        Находит все аннотации для элемента кода Kotlin.
        
        В Kotlin аннотации находятся внутри узла modifiers.
        
        Args:
            node: Узел элемента
            
        Returns:
            Список узлов аннотаций
        """
        annotations = []
        
        # Ищем modifiers среди дочерних узлов
        for child in node.children:
            if child.type == "modifiers":
                # Собираем все аннотации внутри modifiers
                for modifier_child in child.children:
                    if modifier_child.type == "annotation":
                        annotations.append(modifier_child)
        
        return annotations

    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Собирает Kotlin-специфичные приватные элементы.
        
        Включает object declarations, properties и companion objects.
        
        Returns:
            Список Kotlin-специфичных приватных элементов
        """
        private_elements = []
        
        # Собираем object declarations
        self._collect_objects(private_elements)
        
        # Собираем properties (свойства Kotlin)
        self._collect_properties(private_elements)
        
        # Собираем companion objects
        self._collect_companion_objects(private_elements)
        
        return private_elements
    
    def _collect_objects(self, private_elements: List[ElementInfo]) -> None:
        """Собирает неэкспортируемые object declarations."""
        objects = self.doc.query_opt("objects")
        for node, capture_name in objects:
            if capture_name == "object_name":
                object_def = node.parent
                if object_def:
                    element_info = self.analyze_element(object_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)
    
    def _collect_properties(self, private_elements: List[ElementInfo]) -> None:
        """Собирает приватные/защищенные свойства."""
        properties = self.doc.query_opt("properties")
        for node, capture_name in properties:
            if capture_name == "property_name":
                # Поднимаемся к property_declaration
                property_def = node.parent
                if property_def:
                    property_def = property_def.parent  # variable_declaration -> property_declaration
                if property_def:
                    element_info = self.analyze_element(property_def)
                    if not element_info.in_public_api:
                        private_elements.append(element_info)
    
    def _collect_companion_objects(self, private_elements: List[ElementInfo]) -> None:
        """Собирает companion objects если настроено."""
        # TODO: Реализовать логику для companion objects
        # Companion objects в Kotlin - это статические члены класса
        pass

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Проверяет, является ли узел пробелом или комментарием в Kotlin.
        
        Args:
            node: Tree-sitter узел для проверки
            
        Returns:
            True если узел является пробелом или комментарием
        """
        return node.type in ("line_comment", "multiline_comment", "newline", "\n", " ", "\t")

