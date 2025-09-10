"""
Система анализа структуры кода для языковых адаптеров.
Предоставляет язык-специфичные методы для определения типов элементов,
работы с декораторами и анализа иерархии кода.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .tree_sitter_support import Node, TreeSitterDocument


@dataclass(frozen=True)
class ElementInfo:
    """Информация об элементе кода (функция, метод, класс, интерфейс и т.д.)."""
    node: Node
    element_type: str  # "function", "method", "class", "interface", "type"
    name_node: Optional[Node] = None
    body_node: Optional[Node] = None
    decorators: List[Node] = None

    def __post_init__(self):
        if self.decorators is None:
            object.__setattr__(self, 'decorators', [])


@dataclass(frozen=True)
class FunctionGroup:
    """Группа узлов, относящихся к одной функции/методу."""
    definition: Node
    element_type: str
    name_node: Optional[Node] = None
    body_node: Optional[Node] = None
    decorators: List[Node] = None

    def __post_init__(self):
        if self.decorators is None:
            object.__setattr__(self, 'decorators', [])


class CodeStructureAnalyzer(ABC):
    """
    Абстрактный анализатор структуры кода.
    Каждый языковой адаптер должен предоставить свою реализацию.
    """

    def __init__(self, doc: TreeSitterDocument):
        self.doc = doc

    # ============= Основные методы анализа структуры =============

    @abstractmethod
    def is_method_element(self, node: Node) -> bool:
        """
        Определяет, является ли узел методом класса.
        
        Args:
            node: Tree-sitter узел для анализа
            
        Returns:
            True если узел является методом класса, False если функцией верхнего уровня
        """
        pass

    @abstractmethod
    def get_element_type(self, node: Node) -> str:
        """
        Определяет тип элемента на основе структуры узла.
        
        Args:
            node: Tree-sitter узел
            
        Returns:
            Строка с типом элемента: "function", "method", "class", "interface", "type"
        """
        pass

    @abstractmethod
    def find_function_definition_in_parents(self, node: Node) -> Optional[Node]:
        """
        Находит function_definition для данного узла, поднимаясь по дереву.
        
        Args:
            node: Узел для поиска родительской функции
            
        Returns:
            Function definition или None если не найден
        """
        pass

    @abstractmethod
    def collect_function_like_elements(self, captures: List[Tuple[Node, str]]) -> Dict[Node, FunctionGroup]:
        """
        Группирует захваты Tree-sitter по функциям/методам.
        
        Args:
            captures: Список (node, capture_name) из Tree-sitter запроса
            
        Returns:
            Словарь: function_node -> FunctionGroup с информацией о функции
        """
        pass

    # ============= Методы для работы с декораторами =============

    @abstractmethod
    def get_decorated_definition_types(self) -> Set[str]:
        """
        Возвращает типы узлов для wrapped decorated definitions.
        Это узлы-обертки, которые содержат декораторы и сам элемент.
        """
        pass

    @abstractmethod
    def get_decorator_types(self) -> Set[str]:
        """
        Возвращает типы узлов для отдельных декораторов/аннотаций.
        """
        pass

    def find_decorators_for_element(self, node: Node) -> List[Node]:
        """
        Находит все декораторы/аннотации для элемента кода.
        
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
        # (для случаев где декораторы не обернуты в decorated_definition)
        preceding_decorators = self._find_preceding_decorators(node)
        
        # Объединяем результаты, избегая дубликатов
        all_decorators = decorators + [d for d in preceding_decorators if d not in decorators]
        
        return all_decorators

    def _find_preceding_decorators(self, node: Node) -> List[Node]:
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
            if sibling.type in self.get_decorator_types():
                decorators.insert(0, sibling)  # Вставляем в начало для правильного порядка
            elif self._is_whitespace_or_comment(sibling):
                # Пропускаем комментарии и пробелы между декораторами
                continue
            else:
                # Встретили значимый не-декоратор - прекращаем поиск
                break
        
        return decorators

    def get_element_range_with_decorators(self, node: Node) -> Tuple[int, int]:
        """
        Получает диапазон элемента включая его декораторы/аннотации.
        
        Эта функция решает проблему "висящих" декораторов при удалении элементов.
        Всегда используйте её вместо прямого получения диапазона при удалении элементов.
        
        Args:
            node: Узел элемента (функция, класс, метод)
            
        Returns:
            Tuple (start_byte, end_byte) включая все связанные декораторы
        """
        decorators = self.find_decorators_for_element(node)
        
        if decorators:
            # Берем самый ранний декоратор как начало диапазона
            start_byte = min(decorator.start_byte for decorator in decorators)
            end_byte = node.end_byte
            return start_byte, end_byte
        else:
            # Нет декораторов - используем обычный диапазон элемента
            return self.doc.get_node_range(node)

    def get_element_line_range_with_decorators(self, node: Node) -> Tuple[int, int]:
        """
        Получает диапазон строк элемента включая его декораторы/аннотации.
        
        Args:
            node: Узел элемента
            
        Returns:
            Tuple (start_line, end_line) включая все связанные декораторы
        """
        start_byte, end_byte = self.get_element_range_with_decorators(node)
        start_line = self.doc.get_line_number_for_byte(start_byte)
        end_line = self.doc.get_line_number_for_byte(end_byte)
        return start_line, end_line

    def is_decorator_node(self, node: Node) -> bool:
        """
        Проверяет, является ли узел декоратором/аннотацией.
        
        Args:
            node: Tree-sitter узел для проверки
            
        Returns:
            True если узел является декоратором
        """
        return node.type in self.get_decorator_types()

    def get_decorated_element_from_decorator(self, decorator_node: Node) -> Optional[Node]:
        """
        Находит элемент, к которому относится декоратор.
        
        Args:
            decorator_node: Узел декоратора
            
        Returns:
            Узел декорируемого элемента или None если не найден
        """
        # Если декоратор внутри decorated_definition
        parent = decorator_node.parent
        if parent and parent.type in self.get_decorated_definition_types():
            # Ищем первый не-декораторный дочерний узел
            for child in parent.children:
                if child.type not in self.get_decorator_types() and child != decorator_node:
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
                    if (sibling.type not in self.get_decorator_types() and 
                        not self._is_whitespace_or_comment(sibling)):
                        return sibling
        
        return None

    # ============= Вспомогательные методы =============

    @abstractmethod
    def _is_whitespace_or_comment(self, node: Node) -> bool:
        """
        Проверяет, является ли узел пробелом или комментарием.
        Реализация зависит от языка.
        """
        pass

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
