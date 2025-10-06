"""
Модели данных для системы условий.

Содержит классы для представления различных типов условий в адаптивных шаблонах.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Union


class ConditionType(Enum):
    """Типы условий в системе."""
    TAG = "tag"
    TAGSET = "tagset"
    SCOPE = "scope"
    TASK = "task"
    AND = "and"
    OR = "or"
    NOT = "not"
    GROUP = "group"  # для явной группировки в скобках


@dataclass
class Condition(ABC):
    """Базовый абстрактный класс для всех условий."""
    
    @abstractmethod
    def get_type(self) -> ConditionType:
        """Возвращает тип условия."""
        pass
    
    def __str__(self) -> str:
        """Строковое представление условия."""
        return self._to_string()
    
    @abstractmethod
    def _to_string(self) -> str:
        """Внутренний метод для создания строкового представления."""
        pass


@dataclass
class TagCondition(Condition):
    """
    Условие наличия тега: tag:name
    
    Истинно, если указанный тег активен в текущем контексте.
    """
    name: str
    
    def get_type(self) -> ConditionType:
        return ConditionType.TAG
    
    def _to_string(self) -> str:
        return f"tag:{self.name}"


@dataclass
class TagSetCondition(Condition):
    """
    Условие на набор тегов: TAGSET:set_name:tag_name
    
    Правила оценки:
    - Истинно, если ни один тег из набора не активен
    - Истинно, если указанный тег активен
    - Ложно во всех остальных случаях
    """
    set_name: str
    tag_name: str
    
    def get_type(self) -> ConditionType:
        return ConditionType.TAGSET
    
    def _to_string(self) -> str:
        return f"TAGSET:{self.set_name}:{self.tag_name}"


@dataclass
class ScopeCondition(Condition):
    """
    Условие скоупа: scope:type
    
    Поддерживаемые типы:
    - "local": применяется только в локальном скоупе
    - "parent": применяется только при рендере из родительского скоупа
    """
    scope_type: str  # "local" или "parent"
    
    def get_type(self) -> ConditionType:
        return ConditionType.SCOPE
    
    def _to_string(self) -> str:
        return f"scope:{self.scope_type}"


@dataclass
class TaskCondition(Condition):
    """
    Условие наличия task: task
    
    Истинно, если задан непустой текст задачи через --task.
    """
    
    def get_type(self) -> ConditionType:
        return ConditionType.TASK
    
    def _to_string(self) -> str:
        return "task"


@dataclass
class GroupCondition(Condition):
    """
    Группа условий в скобках: (condition)
    
    Используется для явной группировки и изменения приоритета операторов.
    """
    condition: Condition
    
    def get_type(self) -> ConditionType:
        return ConditionType.GROUP
    
    def _to_string(self) -> str:
        return f"({self.condition})"


@dataclass
class NotCondition(Condition):
    """
    Отрицание условия: NOT condition
    
    Инвертирует результат вычисления вложенного условия.
    """
    condition: Condition
    
    def get_type(self) -> ConditionType:
        return ConditionType.NOT
    
    def _to_string(self) -> str:
        return f"NOT {self.condition}"


@dataclass
class BinaryCondition(Condition):
    """
    Бинарная операция: left op right
    
    Поддерживаемые операторы:
    - AND: истинно, если оба операнда истинны
    - OR: истинно, если хотя бы один операнд истинен
    """
    left: Condition
    right: Condition
    operator: ConditionType  # AND или OR
    
    def get_type(self) -> ConditionType:
        return self.operator
    
    def _to_string(self) -> str:
        op_str = "AND" if self.operator == ConditionType.AND else "OR"
        return f"{self.left} {op_str} {self.right}"


# Объединенный тип для всех условий
AnyCondition = Union[
    TagCondition,
    TagSetCondition,
    ScopeCondition,
    TaskCondition,
    GroupCondition,
    NotCondition,
    BinaryCondition,
]

__all__ = [
    "Condition",
    "ConditionType",
    "TagCondition",
    "TagSetCondition",
    "ScopeCondition",
    "TaskCondition",
    "GroupCondition",
    "NotCondition",
    "BinaryCondition",
]