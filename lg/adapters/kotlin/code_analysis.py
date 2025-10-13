"""
Kotlin-специфичная реализация унифицированного анализатора кода.
Объединяет функциональность анализа структуры и видимости для Kotlin.
"""

from __future__ import annotations

from typing import List, Optional, Set, Tuple, Dict

from ..code_analysis import CodeAnalyzer, Visibility, ExportStatus, ElementInfo, FunctionGroup
from ..tree_sitter_support import Node


class KotlinCodeAnalyzer(CodeAnalyzer):
    """Kotlin-специфичная реализация унифицированного анализатора кода."""

    def determine_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента Kotlin на основе структуры узла.
        
        Args:
            node: Tree-sitter узел
            
        Returns:
            Строка с типом элемента: "function", "method", "class", "object", "property", "lambda"
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
        elif node_type == "lambda_literal":
            return "lambda"
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
        # Для lambda_literal пытаемся найти имя из property_declaration
        if node.type == "lambda_literal":
            # Лямбда - это часть property_declaration: val name = { ... }
            parent = node.parent
            if parent and parent.type == "property_declaration":
                for child in parent.children:
                    if child.type == "variable_declaration":
                        for grandchild in child.children:
                            if grandchild.type == "identifier":
                                return self.doc.get_node_text(grandchild)
            return None  # Anonymous lambda
        
        # Для property_declaration ищем variable_declaration
        if node.type == "property_declaration":
            for child in node.children:
                if child.type == "variable_declaration":
                    for grandchild in child.children:
                        if grandchild.type == "identifier":
                            return self.doc.get_node_text(grandchild)
        
        # Ищем дочерний узел с именем (identifier)
        for child in node.children:
            if child.type == "identifier":
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
        Находит function_declaration или lambda_literal для данного узла, поднимаясь по дереву.
        
        Args:
            node: Узел для поиска родительской функции
            
        Returns:
            Function definition или None если не найден
        """
        current = node.parent
        while current:
            if current.type in ("function_declaration", "lambda_literal"):
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

    def collect_function_like_elements(self, captures: List[Tuple[Node, str]]) -> Dict[Node, FunctionGroup]:
        """
        Kotlin-специфичная группировка функций и лямбд.
        
        Переопределяет базовый метод для корректной обработки lambda_literal.
        """
        function_groups = {}
        
        # Собираем определения
        for node, capture_name in captures:
            if self.is_function_definition_capture(capture_name):
                element_info = self.analyze_element(node)
                
                # Для лямбд извлекаем тело особым образом
                body_node = None
                if node.type == "lambda_literal":
                    body_node = self.extract_lambda_body(node)
                
                function_groups[node] = FunctionGroup(
                    definition=node,
                    element_info=element_info,
                    body_node=body_node
                )
        
        # Для обычных функций ищем тела через стандартную логику
        for node, capture_name in captures:
            if self.is_function_body_capture(capture_name):
                func_def = self.find_function_definition_in_parents(node)
                if func_def and func_def in function_groups:
                    # Только для function_declaration, не для lambda
                    if func_def.type == "function_declaration":
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
        
        return function_groups
    
    def collect_language_specific_private_elements(self) -> List[ElementInfo]:
        """
        Собирает Kotlin-специфичные приватные элементы.
        
        Включает object declarations, properties.
        
        Returns:
            Список Kotlin-специфичных приватных элементов
        """
        private_elements = []
        
        # Собираем object declarations
        self._collect_objects(private_elements)
        
        # Собираем properties (свойства Kotlin)
        self._collect_properties(private_elements)

        # Собираем неправильно распарсенные классы (с множественными аннотациями)
        self._collect_misparsed_classes(private_elements)
        
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

    def _collect_misparsed_classes(self, private_elements: List[ElementInfo]) -> None:
        """
        Собирает классы, которые Tree-sitter неправильно распарсил.
        
        Проблема: Tree-sitter Kotlin иногда неправильно парсит классы с множественными
        аннотациями на отдельных строках перед модификатором видимости.
        Вместо class_declaration создается annotated_expression -> infix_expression.
        
        Этот метод ищет такие конструкции напрямую в тексте и проверяет их видимость.
        """
        # Ищем все узлы типа "infix_expression", которые могут быть неправильно распарсенными классами
        def find_infix_expressions(node):
            """Рекурсивно находит все infix_expression узлы"""
            results = []
            if node.type == "infix_expression":
                results.append(node)
            for child in node.children:
                results.extend(find_infix_expressions(child))
            return results
        
        infix_nodes = find_infix_expressions(self.doc.root_node)
        
        for infix_node in infix_nodes:
            # Получаем текст узла
            node_text = self.doc.get_node_text(infix_node)
            
            # Нормализуем к строке
            if isinstance(node_text, bytes):
                text_str = node_text.decode('utf-8', errors='ignore')
            else:
                text_str = node_text
            
            # Проверяем, содержит ли текст "private class" или "protected class"
            if "private class" not in text_str and "protected class" not in text_str:
                continue
            
            # Это вероятно неправильно распарсенный класс
            # Определяем видимость из текста
            if "private" in text_str:
                visibility = Visibility.PRIVATE
            elif "protected" in text_str:
                visibility = Visibility.PROTECTED
            else:
                continue  # Не приватный/защищенный - пропускаем
            
            # Извлекаем имя класса (после "class ")
            import re
            class_match = re.search(r'\b(?:private|protected)\s+class\s+(\w+)', text_str)
            if class_match:
                class_name = class_match.group(1)
            else:
                class_name = None
            
            # Ищем аннотации перед этим узлом
            decorators = self._find_annotations_before_node(infix_node)
            
            # Создаем ElementInfo
            element_info = ElementInfo(
                node=infix_node,
                element_type="class",
                name=class_name,
                visibility=visibility,
                export_status=ExportStatus.NOT_EXPORTED,
                is_method=False,
                decorators=decorators
            )
            
            private_elements.append(element_info)
    
    def _find_annotations_before_node(self, node: Node) -> List[Node]:
        """
        Находит аннотации перед узлом, поднимаясь по дереву annotated_expression.
        
        Args:
            node: Узел для поиска аннотаций
            
        Returns:
            Список узлов аннотаций
        """
        annotations = []
        
        # Поднимаемся по родителям, собирая annotated_expression
        current = node.parent
        while current and current.type == "annotated_expression":
            # Ищем аннотации среди детей annotated_expression
            for child in current.children:
                if child.type == "annotation":
                    annotations.insert(0, child)  # Вставляем в начало для правильного порядка
            current = current.parent
        
        return annotations

    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Проверяет, является ли узел пробелом или комментарием в Kotlin.
        
        Args:
            node: Tree-sitter узел для проверки
            
        Returns:
            True если узел является пробелом или комментарием
        """
        return node.type in ("line_comment", "multiline_comment", "newline", "\n", " ", "\t")
    
    def extract_lambda_body(self, lambda_node: Node) -> Optional[Node]:
        """
        Извлекает тело лямбда-функции Kotlin.
        
        Структура lambda_literal:
        - { открывающая скобка
        - lambda_parameters? (опционально)
        - -> (опционально, если есть параметры)
        - тело (statements)
        - } закрывающая скобка
        
        Args:
            lambda_node: Узел lambda_literal
            
        Returns:
            Узел, представляющий тело лямбды (или None для однострочных)
        """
        if lambda_node.type != "lambda_literal":
            return None
        
        # Для однострочных лямбд не удаляем тело
        start_line, end_line = self.doc.get_line_range(lambda_node)
        if start_line == end_line:
            return None  # Single-line lambda, don't strip
        
        # Создаем синтетический узел для тела лямбды
        # Тело начинается после -> (если есть) или после {
        body_start_idx = 0
        has_arrow = False
        
        for i, child in enumerate(lambda_node.children):
            if child.type == "->":
                has_arrow = True
                body_start_idx = i + 1
                break
            elif child.type == "{":
                body_start_idx = i + 1
        
        # Тело заканчивается перед }
        body_end_idx = len(lambda_node.children) - 1
        for i in range(len(lambda_node.children) - 1, -1, -1):
            if lambda_node.children[i].type == "}":
                body_end_idx = i
                break
        
        # Если нет тела (пустая лямбда или только параметры)
        if body_start_idx >= body_end_idx:
            return None
        
        # Возвращаем диапазон от первого statement до последнего
        first_statement = lambda_node.children[body_start_idx]
        last_statement = lambda_node.children[body_end_idx - 1]
        
        # Создаем синтетический узел-обертку
        class LambdaBodyRange:
            def __init__(self, start_node, end_node):
                self.start_byte = start_node.start_byte
                self.end_byte = end_node.end_byte
                self.start_point = start_node.start_point
                self.end_point = end_node.end_point
                self.type = "lambda_body"
        
        return LambdaBodyRange(first_statement, last_statement)

