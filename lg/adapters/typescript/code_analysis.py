"""
TypeScript-специфичная реализация унифицированного анализатора кода.
Объединяет функциональность анализа структуры и видимости для TypeScript.
"""

from __future__ import annotations

from typing import List, Optional, Set

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, PrivateElement, ElementInfo
from ..tree_sitter_support import Node


class TypeScriptCodeAnalyzer(CodeAnalyzer):
    """TypeScript-специфичная реализация унифицированного анализатора кода."""

    def determine_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента TypeScript на основе структуры узла.
        
        Args:
            node: Tree-sitter узел
            
        Returns:
            Строка с типом элемента: "function", "method", "class", "interface", "type"
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
            return "method" if self.is_method_context(node) else "function"
        elif node_type == "method_definition":
            return "method"
        elif node_type == "variable_declaration":
            return "variable"
        else:
            # Fallback: пытаемся определить по родительскому контексту
            if self.is_method_context(node):
                return "method"
            else:
                return "function"

    def extract_element_name(self, node: Node) -> Optional[str]:
        """
        Извлекает имя элемента TypeScript из узла Tree-sitter.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Имя элемента или None если не найдено
        """
        # Специальная обработка для variable_declaration
        if node.type == "variable_declaration":
            # Ищем variable_declarator с именем
            for child in node.children:
                if child.type == "variable_declarator":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return self.doc.get_node_text(grandchild)
        
        # Ищем дочерний узел с именем функции/класса/метода
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "property_identifier"):
                return self.doc.get_node_text(child)
        
        # Для некоторых типов узлов имя может быть в поле name
        name_node = node.child_by_field_name("name")
        if name_node:
            return self.doc.get_node_text(name_node)
        
        return None

    def determine_visibility(self, node: Node) -> Visibility:
        """
        Определяет видимость элемента TypeScript по модификаторам доступа.
        
        Правила TypeScript:
        - Элементы с модификатором 'private' - приватные
        - Элементы с модификатором 'protected' - защищенные  
        - Элементы с модификатором 'public' или без модификатора - публичные
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Уровень видимости элемента
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
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            Статус экспорта элемента
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

    def is_method_context(self, node: Node) -> bool:
        """
        Определяет, является ли узел методом класса TypeScript.
        
        Args:
            node: Tree-sitter узел для анализа
            
        Returns:
            True если узел является методом класса, False если функцией верхнего уровня
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

    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Находит function_definition для данного узла, поднимаясь по дереву.
        
        Args:
            node: Узел для поиска родительской функции
            
        Returns:
            Function definition или None если не найден
        """
        current = node.parent
        while current:
            if current.type in ("function_declaration", "method_definition", "arrow_function"):
                return current
            current = current.parent
        return None

    def find_decorators_for_element(self, node: Node) -> List[Node]:
        """
        Находит все декораторы/аннотации для элемента кода TypeScript.
        
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

    def get_decorated_definition_types(self) -> Set[str]:
        """
        Возвращает типы узлов для wrapped decorated definitions в TypeScript.
        
        Returns:
            Множество типов узлов
        """
        return {
            "decorated_definition",    # TypeScript decorators
            "decorator_list",         # Alternative naming
        }

    def get_decorator_types(self) -> Set[str]:
        """
        Возвращает типы узлов для отдельных декораторов в TypeScript.
        
        Returns:
            Множество типов узлов
        """
        return {
            "decorator",              # TypeScript @decorator
            "decorator_expression",   # TypeScript decorator expressions
        }

    def collect_language_specific_private_elements(self, context) -> List[PrivateElement]:
        """
        Собирает TypeScript-специфичные приватные элементы.
        
        Включает интерфейсы, типы, пространства имен, енумы, поля классов, импорты и переменные.
        
        Args:
            context: Контекст обработки
            
        Returns:
            Список TypeScript-специфичных приватных элементов
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
                    element_info = self.analyze_element(interface_def)
                    if not element_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(element_info))
    
    def _collect_types(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые алиасы типов."""
        types = context.doc.query_opt("types")
        for node, capture_name in types:
            if capture_name == "type_name":
                type_def = node.parent
                if type_def:
                    element_info = self.analyze_element(type_def)
                    if not element_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(element_info))
    
    def _collect_namespaces(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые пространства имен."""
        namespaces = context.doc.query_opt("namespaces")
        for node, capture_name in namespaces:
            if capture_name == "namespace_name":
                namespace_def = node.parent
                if namespace_def:
                    element_info = self.analyze_element(namespace_def)
                    if not element_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(element_info))
    
    def _collect_enums(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые енумы."""
        enums = context.doc.query_opt("enums")
        for node, capture_name in enums:
            if capture_name == "enum_name":
                enum_def = node.parent
                if enum_def:
                    element_info = self.analyze_element(enum_def)
                    if not element_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(element_info))
    
    def _collect_class_members(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает приватные/защищенные члены классов."""
        class_fields = context.doc.query_opt("class_fields")
        for node, capture_name in class_fields:
            if capture_name in ("field_name", "method_name"):
                field_def = node.parent
                if field_def:
                    element_info = self.analyze_element(field_def)
                    if not element_info.should_be_included_in_public_api:
                        # For fields, extend range to include semicolon if present
                        element_type = "field" if capture_name == "field_name" else "method"
                        if element_type == "field":
                            element_with_punctuation = self._extend_range_for_semicolon(field_def)
                            # Create new ElementInfo with extended node
                            element_info = ElementInfo(
                                node=element_with_punctuation,
                                element_type=element_info.element_type,
                                name=element_info.name,
                                visibility=element_info.visibility,
                                export_status=element_info.export_status,
                                is_method=element_info.is_method,
                                decorators=element_info.decorators
                            )
                        private_elements.append(PrivateElement(element_info))
    
    def _collect_imports(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает не-ре-экспортируемые импорты."""
        imports = context.doc.query_opt("imports")
        for node, capture_name in imports:
            if capture_name == "import":
                # Для режима public API оставляем только импорты, которые ре-экспортируются
                import_text = self.doc.get_node_text(node)
                
                # Оставляем только side-effect импорты (без именованных импортов)
                if not any(keyword in import_text for keyword in ["{", "import ", "* as", "from"]):
                    continue  # Оставляем side-effect импорты
                
                # Проверяем, ре-экспортируется ли этот импорт где-то еще
                element_info = self.analyze_element(node)
                private_elements.append(PrivateElement(element_info))
    
    def _collect_variables(self, context, private_elements: List[PrivateElement]) -> None:
        """Собирает неэкспортируемые переменные."""
        variables = context.doc.query_opt("variables")
        for node, capture_name in variables:
            if capture_name == "variable_name":
                variable_def = node.parent.parent  # variable_declarator -> variable_declaration
                if variable_def:
                    element_info = self.analyze_element(variable_def)
                    
                    # Для top-level переменных проверяем публичность и экспорт
                    if not element_info.should_be_included_in_public_api:
                        private_elements.append(PrivateElement(element_info))

    def _check_export_in_source_line(self, node: Node) -> bool:
        """
        Проверяет наличие 'export' в исходной строке элемента.
        Это fallback для случаев, когда Tree-sitter не правильно парсит export.
        
        Args:
            node: Tree-sitter узел элемента
            
        Returns:
            True если найден export в начале строки
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
        
        Args:
            node: Tree-sitter узел
            
        Returns:
            Узел с расширенным диапазоном или оригинальный узел
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
        
        Args:
            original_node: Оригинальный узел
            semicolon_node: Узел точки с запятой
            
        Returns:
            Объект с расширенным диапазоном
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

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Проверяет, является ли узел пробелом или комментарием в TypeScript.
        
        Args:
            node: Tree-sitter узел для проверки
            
        Returns:
            True если узел является пробелом или комментарием
        """
        return node.type in ("comment", "line_comment", "block_comment", "newline", "\n", " ", "\t")
