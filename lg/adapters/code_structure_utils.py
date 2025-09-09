"""
Utility functions for Tree-sitter node analysis in optimizations.
Provides common functions for determining node types and relationships.
"""

from __future__ import annotations

from typing import Optional, List, Set, Tuple

from lg.adapters.tree_sitter_support import Node, TreeSitterDocument


def is_method_node(node: Node) -> bool:
    """
    Определяет, является ли узел методом класса.
    Универсальная функция, которая работает для разных языков.
    
    Args:
        node: Tree-sitter узел для анализа
        
    Returns:
        True если узел является методом класса, False если функцией верхнего уровня
    """
    # Проходим вверх по дереву в поисках определения класса
    current = node.parent
    while current:
        if current.type in ("class_definition", "class_declaration", "class_body"):
            return True
        # Останавливаемся на границах модуля/файла
        if current.type in ("program", "source_file", "module"):
            break
        current = current.parent
    return False


def find_function_definition_in_parents(node: Node) -> Optional[Node]:
    """
    Находит function_definition для данного узла, поднимаясь по дереву.
    
    Args:
        node: Узел для поиска родительской функции
        
    Returns:
        Function definition или None если не найден
    """
    current = node.parent
    while current:
        if current.type in ("function_definition", "method_definition", "arrow_function", 
                           "function_declaration"):
            return current
        current = current.parent
    return None


def get_element_type_from_node(node: Node) -> str:
    """
    Определяет тип элемента на основе структуры узла.
    
    Args:
        node: Tree-sitter узел
        
    Returns:
        Строка с типом элемента: "function", "method", "class", "interface", "type"
    """
    node_type = node.type
    
    # Прямое соответствие типов узлов
    if node_type in ("class_definition", "class_declaration"):
        return "class"
    elif node_type in ("interface_declaration",):
        return "interface"
    elif node_type in ("type_alias_declaration",):
        return "type"
    elif node_type in ("function_definition", "function_declaration", "arrow_function"):
        # Определяем функция это или метод по контексту
        return "method" if is_method_node(node) else "function"
    elif node_type in ("method_definition",):
        return "method"
    else:
        # Fallback: пытаемся определить по родительскому контексту
        if is_method_node(node):
            return "method"
        else:
            return "function"


def collect_function_like_nodes(captures: list[tuple[Node, str]]) -> dict[Node, dict]:
    """
    Группирует захваты Tree-sitter по функциям/методам.
    
    Args:
        captures: Список (node, capture_name) из Tree-sitter запроса
        
    Returns:
        Словарь: function_node -> {"definition": node, "body": node, "name": node, "type": str}
    """
    function_groups = {}
    
    # Сначала собираем все определения функций
    for node, capture_name in captures:
        if capture_name in ("function_definition", "method_definition"):
            function_groups[node] = {
                "definition": node,
                "type": get_element_type_from_node(node)
            }
    
    # Затем ищем соответствующие тела и имена
    for node, capture_name in captures:
        if capture_name in ("function_body", "method_body"):
            # Ищем соответствующее определение функции
            func_def = find_function_definition_in_parents(node)
            if func_def and func_def in function_groups:
                function_groups[func_def]["body"] = node
        
        elif capture_name in ("function_name", "method_name"):
            # Ищем соответствующее определение функции
            func_def = find_function_definition_in_parents(node)
            if func_def and func_def in function_groups:
                function_groups[func_def]["name"] = node
    
    # Обрабатываем случаи когда нет явного definition в захватах
    for node, capture_name in captures:
        if capture_name in ("function_name", "method_name") and node not in function_groups:
            # Создаем группу на основе имени
            func_def = find_function_definition_in_parents(node)
            if func_def and func_def not in function_groups:
                function_groups[func_def] = {
                    "definition": func_def,
                    "name": node,
                    "type": get_element_type_from_node(func_def)
                }
    
    return function_groups


# ============= Функции для работы с декораторами/аннотациями =============

def get_decorated_definition_types() -> Set[str]:
    """
    Возвращает типы узлов для wrapped decorated definitions.
    Это узлы-обертки, которые содержат декораторы и сам элемент.
    """
    return {
        "decorated_definition",    # Python
        "decorator_list",         # Some languages  
        "decorated_item",         # Alternative naming
        "annotation_list",        # Java/C# style
    }


def get_decorator_types() -> Set[str]:
    """
    Возвращает типы узлов для отдельных декораторов/аннотаций.
    """
    return {
        "decorator",              # Python @decorator
        "annotation",            # Java @Annotation, C# [Attribute]
        "attribute",             # Alternative naming
        "decorator_expression",  # Some grammars
        "annotation_expression", # TypeScript decorators
    }


def find_decorators_for_element(node: Node, doc: TreeSitterDocument) -> List[Node]:
    """
    Находит все декораторы/аннотации для элемента кода.
    
    Работает в двух режимах:
    1. Если элемент обернут в decorated_definition - извлекает декораторы из него
    2. Иначе ищет декораторы среди предыдущих sibling узлов
    
    Args:
        node: Узел элемента (функция, класс, метод)
        doc: Tree-sitter документ
        
    Returns:
        Список узлов декораторов в порядке их появления в коде
    """
    decorators = []
    
    # Режим 1: Проверяем parent на decorated_definition
    parent = node.parent
    if parent and parent.type in get_decorated_definition_types():
        # Ищем дочерние узлы-декораторы в wrapped definition
        for child in parent.children:
            if child.type in get_decorator_types():
                decorators.append(child)
            elif child == node:
                # Дошли до самого элемента - прекращаем поиск
                break
    
    # Режим 2: Ищем декораторы среди предыдущих sibling узлов
    # (для случаев где декораторы не обернуты в decorated_definition)
    preceding_decorators = find_preceding_decorators(node)
    
    # Объединяем результаты, избегая дубликатов
    all_decorators = decorators + [d for d in preceding_decorators if d not in decorators]
    
    return all_decorators


def find_preceding_decorators(node: Node) -> List[Node]:
    """
    Находит декораторы/аннотации среди предыдущих sibling узлов.
    
    Args:
        node: Узел элемента
        
    Returns:
        Список узлов декораторов в порядке их появления
    """
    decorators = []
    
    if not node.parent:
        return decorators
    
    # Находим позицию node среди siblings
    siblings = node.parent.children
    node_index = None
    for i, sibling in enumerate(siblings):
        if sibling == node:
            node_index = i
            break
    
    if node_index is None:
        return decorators
    
    # Проверяем предыдущие siblings на декораторы
    # Идем назад до первого не-декоратора
    for i in range(node_index - 1, -1, -1):
        sibling = siblings[i]
        if sibling.type in get_decorator_types():
            decorators.insert(0, sibling)  # Вставляем в начало для правильного порядка
        elif sibling.type in ("comment", "whitespace"):
            # Пропускаем комментарии и пробелы между декораторами
            continue
        else:
            # Встретили значимый не-декоратор - прекращаем поиск
            break
    
    return decorators


def get_element_range_with_decorators(node: Node, doc: TreeSitterDocument) -> Tuple[int, int]:
    """
    Получает диапазон элемента включая его декораторы/аннотации.
    
    Эта функция решает проблему "висящих" декораторов при удалении элементов.
    Всегда используйте её вместо прямого получения диапазона при удалении элементов.
    
    Args:
        node: Узел элемента (функция, класс, метод)
        doc: Tree-sitter документ
        
    Returns:
        Tuple (start_byte, end_byte) включая все связанные декораторы
    """
    decorators = find_decorators_for_element(node, doc)
    
    if decorators:
        # Берем самый ранний декоратор как начало диапазона
        start_byte = min(decorator.start_byte for decorator in decorators)
        end_byte = node.end_byte
        return start_byte, end_byte
    else:
        # Нет декораторов - используем обычный диапазон элемента
        return doc.get_node_range(node)


def get_element_line_range_with_decorators(node: Node, doc: TreeSitterDocument) -> Tuple[int, int]:
    """
    Получает диапазон строк элемента включая его декораторы/аннотации.
    
    Args:
        node: Узел элемента
        doc: Tree-sitter документ
        
    Returns:
        Tuple (start_line, end_line) включая все связанные декораторы
    """
    start_byte, end_byte = get_element_range_with_decorators(node, doc)
    start_line = doc.get_line_number_for_byte(start_byte)
    end_line = doc.get_line_number_for_byte(end_byte)
    return start_line, end_line


def is_decorator_node(node: Node) -> bool:
    """
    Проверяет, является ли узел декоратором/аннотацией.
    
    Args:
        node: Tree-sitter узел для проверки
        
    Returns:
        True если узел является декоратором
    """
    return node.type in get_decorator_types()


def get_decorated_element_from_decorator(decorator_node: Node) -> Optional[Node]:
    """
    Находит элемент, к которому относится декоратор.
    
    Args:
        decorator_node: Узел декоратора
        
    Returns:
        Узел декорируемого элемента или None если не найден
    """
    # Если декоратор внутри decorated_definition
    parent = decorator_node.parent
    if parent and parent.type in get_decorated_definition_types():
        # Ищем первый не-декораторный дочерний узел
        for child in parent.children:
            if child.type not in get_decorator_types() and child != decorator_node:
                return child
    
    # Ищем следующий sibling, который не является декоратором
    if parent:
        siblings = parent.children
        decorator_index = None
        for i, sibling in enumerate(siblings):
            if sibling == decorator_node:
                decorator_index = i
                break
        
        if decorator_index is not None:
            # Ищем следующий значимый элемент
            for i in range(decorator_index + 1, len(siblings)):
                sibling = siblings[i]
                if sibling.type not in get_decorator_types() and sibling.type not in ("comment", "whitespace"):
                    return sibling
    
    return None
