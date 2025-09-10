"""
TypeScript-specific visibility analysis.
"""

from __future__ import annotations

from typing import List, Optional

from ..visibility_analysis import VisibilityAnalyzer, Visibility, ExportStatus, PrivateElement
from ..tree_sitter_support import Node


class TypeScriptVisibilityAnalyzer(VisibilityAnalyzer):
    """TypeScript-specific implementation of visibility analyzer."""

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Определяет видимость элемента TypeScript по модификаторам доступа.
        
        Правила TypeScript:
        - Элементы с модификатором 'private' - приватные
        - Элементы с модификатором 'protected' - защищенные  
        - Элементы с модификатором 'public' или без модификатора - публичные
        """
        node_text = self.doc.get_node_text(node)
        
        # Ищем модификаторы доступа среди дочерних узлов
        for child in node.children:
            if child.type == "accessibility_modifier":
                modifier_text = self.doc.get_node_text(child)
                if modifier_text == "private":
                    return Visibility.PRIVATE
                elif modifier_text == "protected":
                    return Visibility.PROTECTED
                elif modifier_text == "public":
                    return Visibility.PUBLIC
        
        # Fallback: проверяем в тексте узла наличие модификаторов
        if "private " in node_text or node_text.strip().startswith("private "):
            return Visibility.PRIVATE
        if "protected " in node_text or node_text.strip().startswith("protected "):
            return Visibility.PROTECTED
        
        # Если модификатор не найден, элемент считается публичным по умолчанию
        return Visibility.PUBLIC

    def determine_export_status(self, node: Node) -> ExportStatus:
        """
        Определяет статус экспорта элемента TypeScript.
        
        Правила:
        - Методы внутри классов НЕ считаются экспортируемыми 
        - Top-level функции, классы, интерфейсы экспортируются если есть export
        - Приватные/защищенные методы никогда не экспортируются
        """
        # Если это метод внутри класса, он НЕ экспортируется напрямую
        if node.type == "method_definition":
            return ExportStatus.NOT_EXPORTED
        
        # Проверяем, что это top-level элемент с export
        node_text = self.doc.get_node_text(node)
        
        # Простая проверка: элемент экспортируется если непосредственно перед ним стоит export
        if node_text.strip().startswith("export "):
            return ExportStatus.EXPORTED
        
        # Проверяем parent для export statement
        current = node
        while current and current.type not in ("program", "source_file"):
            if current.type == "export_statement":
                return ExportStatus.EXPORTED
            current = current.parent
        
        # Дополнительная проверка через поиск export в начале строки
        if self._check_export_in_source_line(node):
            return ExportStatus.EXPORTED
        
        return ExportStatus.NOT_EXPORTED

    def is_method_element(self, node: Node) -> bool:
        """
        Определяет, является ли узел методом класса TypeScript.
        """
        # Проходим вверх по дереву в поисках определения класса
        current = node.parent
        while current:
            if current.type in ("class_declaration", "class_body"):
                return True
            # Останавливаемся на границах модуля/файла
            if current.type in ("program", "source_file"):
                break
            current = current.parent
        return False

    def get_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента TypeScript на основе структуры узла.
        """
        node_type = node.type
        
        # Прямое соответствие типов узлов
        if node_type == "class_declaration":
            return "class"
        elif node_type == "interface_declaration":
            return "interface"
        elif node_type == "type_alias_declaration":
            return "type"
        elif node_type in ("function_declaration", "arrow_function"):
            # Определяем функция это или метод по контексту
            return "method" if self.is_method_element(node) else "function"
        elif node_type == "method_definition":
            return "method"
        else:
            # Fallback: пытаемся определить по родительскому контексту
            if self.is_method_element(node):
                return "method"
            else:
                return "function"

    def _collect_language_specific_elements(self, context) -> List[PrivateElement]:
        """
        Собирает TypeScript-специфичные приватные элементы.
        
        Включает интерфейсы, типы, пространства имен, енумы, поля классов, импорты и переменные.
        """
        private_elements = []
        
        # TypeScript-специфичные элементы
        self._collect_interfaces(context, private_elements)
        self._collect_types(context, private_elements)
        self._collect_namespaces(context, private_elements)
        self._collect_enums(context, private_elements)
        self._collect_class_members(context, private_elements)
        self._collect_imports(context, private_elements)
        self._collect_variables(context, private_elements)
        
        return private_elements
    
    def _collect_interfaces(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые интерфейсы."""
        interfaces = context.doc.query_opt("interfaces")
        for node, capture_name in interfaces:
            if capture_name == "interface_name":
                interface_def = node.parent
                if interface_def:
                    visibility_info = self.analyze_element_visibility(interface_def)
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=interface_def,
                            element_type="interface", 
                            visibility_info=visibility_info
                        ))
    
    def _collect_types(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые алиасы типов."""
        types = context.doc.query_opt("types")
        for node, capture_name in types:
            if capture_name == "type_name":
                type_def = node.parent
                if type_def:
                    visibility_info = self.analyze_element_visibility(type_def)
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=type_def,
                            element_type="type",
                            visibility_info=visibility_info
                        ))
    
    def _collect_namespaces(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые пространства имен."""
        namespaces = context.doc.query_opt("namespaces")
        for node, capture_name in namespaces:
            if capture_name == "namespace_name":
                namespace_def = node.parent
                if namespace_def:
                    visibility_info = self.analyze_element_visibility(namespace_def)
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=namespace_def,
                            element_type="namespace",
                            visibility_info=visibility_info
                        ))
    
    def _collect_enums(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые енумы."""
        enums = context.doc.query_opt("enums")
        for node, capture_name in enums:
            if capture_name == "enum_name":
                enum_def = node.parent
                if enum_def:
                    visibility_info = self.analyze_element_visibility(enum_def)
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=enum_def,
                            element_type="enum",
                            visibility_info=visibility_info
                        ))
    
    def _collect_class_members(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает приватные/защищенные члены классов."""
        class_fields = context.doc.query_opt("class_fields")
        for node, capture_name in class_fields:
            if capture_name in ("field_name", "method_name"):
                field_def = node.parent
                if field_def:
                    visibility_info = self.analyze_element_visibility(field_def)
                    if not visibility_info.should_be_included_in_public_api:
                        element_type = "field" if capture_name == "field_name" else "method"
                        # For fields, extend range to include semicolon if present
                        element_with_punctuation = self._extend_range_for_semicolon(field_def) if element_type == "field" else field_def
                        private_elements.append(PrivateElement(
                            node=element_with_punctuation,
                            element_type=element_type,
                            visibility_info=visibility_info
                        ))
    
    def _collect_imports(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает не-ре-экспортируемые импорты."""
        imports = context.doc.query_opt("imports")
        for node, capture_name in imports:
            if capture_name == "import":
                # Для режима public API оставляем только импорты, которые ре-экспортируются
                # Для простоты, удаляем все импорты, которые не являются явными ре-экспортами
                # Это консервативный подход - можно доработать для проверки ре-экспортов
                import_text = self.doc.get_node_text(node)
                
                # Оставляем только side-effect импорты (без именованных импортов)
                if not any(keyword in import_text for keyword in ["{", "import ", "* as", "from"]):
                    continue  # Оставляем side-effect импорты
                
                # Проверяем, ре-экспортируется ли этот импорт где-то еще
                # Пока удаляем все обычные импорты в режиме public API
                visibility_info = self.analyze_element_visibility(node)
                private_elements.append(PrivateElement(
                    node=node,
                    element_type="import",
                    visibility_info=visibility_info
                ))
    
    def _collect_variables(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые переменные."""
        assignments = context.doc.query_opt("assignments")
        for node, capture_name in assignments:
            if capture_name == "variable_name":
                assignment_def = node.parent
                if assignment_def:
                    visibility_info = self.analyze_element_visibility(assignment_def)
                    
                    # Для top-level переменных проверяем публичность и экспорт
                    if not visibility_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(
                            node=assignment_def,
                            element_type="variable",
                            visibility_info=visibility_info
                        ))

    def _check_export_in_source_line(self, node: Node) -> bool:
        """
        Проверяет наличие 'export' в исходной строке элемента.
        Это fallback для случаев, когда Tree-sitter не правильно парсит export.
        """
        start_line, _ = self.doc.get_line_range(node)
        lines = self.doc.text.split('\n')
        
        if start_line < len(lines):
            line_text = lines[start_line].strip()
            # Простая проверка на наличие export в начале строки
            if line_text.startswith('export '):
                return True
        
        return False

    def _extend_range_for_semicolon(self, node):
        """
        Расширяет диапазон узла для включения завершающей точки с запятой, если она присутствует.
        
        Это нужно для полей TypeScript где точка с запятой является отдельным sibling узлом.
        Без включения её, соседние плейсхолдеры полей не могут быть правильно сколлапсированы.
        """
        # Проверяем, есть ли точка с запятой сразу после этого узла
        parent = node.parent
        if not parent:
            return node
        
        # Находим позицию этого узла среди siblings
        siblings = parent.children
        node_index = None
        for i, sibling in enumerate(siblings):
            if sibling == node:
                node_index = i
                break
        
        if node_index is None:
            return node
        
        # Проверяем, является ли следующий sibling точкой с запятой
        if node_index + 1 < len(siblings):
            next_sibling = siblings[node_index + 1]
            if (next_sibling.type == ";" or 
                self.doc.get_node_text(next_sibling).strip() == ";"):
                # Создаем синтетический диапазон, который включает точку с запятой
                return self._create_extended_range_node(node, next_sibling)
        
        return node
    
    def _create_extended_range_node(self, original_node, semicolon_node):
        """
        Создает синтетический node-подобный объект с расширенным диапазоном.
        
        Это workaround поскольку узлы Tree-sitter неизменяемы.
        Мы создаем простой объект, который имеет тот же интерфейс для операций с диапазонами.
        """
        class ExtendedRangeNode:
            def __init__(self, start_node, end_node):
                self.start_byte = start_node.start_byte
                self.end_byte = end_node.end_byte
                self.start_point = start_node.start_point
                self.end_point = end_node.end_point
                self.type = start_node.type
                self.parent = start_node.parent
                # Копируем другие часто используемые атрибуты
                for attr in ['children', 'text']:
                    if hasattr(start_node, attr):
                        setattr(self, attr, getattr(start_node, attr))
        
        return ExtendedRangeNode(original_node, semicolon_node)
