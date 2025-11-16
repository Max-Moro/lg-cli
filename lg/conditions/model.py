"""
Data models for the conditions system.

Contains classes for representing various types of conditions in adaptive templates.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Union


class ConditionType(Enum):
    """Types of conditions in the system."""
    TAG = "tag"
    TAGSET = "tagset"
    SCOPE = "scope"
    TASK = "task"
    AND = "and"
    OR = "or"
    NOT = "not"
    GROUP = "group"  # for explicit grouping in parentheses


@dataclass
class Condition(ABC):
    """Base abstract class for all conditions."""

    @abstractmethod
    def get_type(self) -> ConditionType:
        """Returns the condition type."""
        pass

    def __str__(self) -> str:
        """String representation of the condition."""
        return self._to_string()

    @abstractmethod
    def _to_string(self) -> str:
        """Internal method for creating string representation."""
        pass


@dataclass
class TagCondition(Condition):
    """
    Tag existence condition: tag:name

    True if the specified tag is active in the current context.
    """
    name: str
    
    def get_type(self) -> ConditionType:
        return ConditionType.TAG
    
    def _to_string(self) -> str:
        return f"tag:{self.name}"


@dataclass
class TagSetCondition(Condition):
    """
    Tag set condition: TAGSET:set_name:tag_name

    Evaluation rules:
    - True if no tags in the set are active
    - True if the specified tag is active
    - False in all other cases
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
    Scope condition: scope:type

    Supported types:
    - "local": applies only in local scope
    - "parent": applies only when rendering from parent scope
    """
    scope_type: str  # "local" or "parent"
    
    def get_type(self) -> ConditionType:
        return ConditionType.SCOPE
    
    def _to_string(self) -> str:
        return f"scope:{self.scope_type}"


@dataclass
class TaskCondition(Condition):
    """
    Task condition: task

    True if a non-empty task text is provided via --task.
    """
    
    def get_type(self) -> ConditionType:
        return ConditionType.TASK
    
    def _to_string(self) -> str:
        return "task"


@dataclass
class GroupCondition(Condition):
    """
    Group of conditions in parentheses: (condition)

    Used for explicit grouping and changing operator precedence.
    """
    condition: Condition
    
    def get_type(self) -> ConditionType:
        return ConditionType.GROUP
    
    def _to_string(self) -> str:
        return f"({self.condition})"


@dataclass
class NotCondition(Condition):
    """
    Negation of a condition: NOT condition

    Inverts the evaluation result of the nested condition.
    """
    condition: Condition
    
    def get_type(self) -> ConditionType:
        return ConditionType.NOT
    
    def _to_string(self) -> str:
        return f"NOT {self.condition}"


@dataclass
class BinaryCondition(Condition):
    """
    Binary operation: left op right

    Supported operators:
    - AND: true if both operands are true
    - OR: true if at least one operand is true
    """
    left: Condition
    right: Condition
    operator: ConditionType  # AND or OR
    
    def get_type(self) -> ConditionType:
        return self.operator
    
    def _to_string(self) -> str:
        op_str = "AND" if self.operator == ConditionType.AND else "OR"
        return f"{self.left} {op_str} {self.right}"


# Union type for all conditions
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