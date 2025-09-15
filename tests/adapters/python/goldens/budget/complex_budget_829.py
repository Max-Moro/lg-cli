"""Comprehensive sample for Budget System tests (Python).

Includes:
- Many external/local imports
- Large literals (strings, lists, dicts)
- Mixed comments and docstrings
- Public/private functions, classes, methods
- If __name__ == '__main__' guard
"""

# External imports (simulate as external for analyzer)
import os
import sys
import json
import re
import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

# Local imports (should be local)
from .utils import helper as local_helper  # type: ignore  # noqa: F401
from ..core.models import User  # type: ignore  # noqa: F401


MODULE_DOC = """
This module demonstrates a variety of language features to exercise the
BudgetController escalation sequence. The text here is quite verbose and
contains enough content to potentially be truncated when budgets are small.

It includes details that are not crucial for code understanding but useful as
payload for trimming policies. The goal is to keep signatures while shrinking
non-essential content.
"""

BIG_LIST = [f"item_{i:04d}" for i in range(200)]

BIG_DICT = {
    "users": [{"id": i, "name": f"User {i}", "active": i % 2 == 0} for i in range(50)],
    "settings": {
        "feature_flags": {f"flag_{i}": bool(i % 2) for i in range(30)},
        "limits": {"max": 1000000, "min": 0, "thresholds": list(range(100))},
    },
}


def public_function(data: str) -> str:
    """Public API function.

    This docstring has multiple sentences. When budget is constrained, the
    controller may reduce documentation to the first sentence.
    """
    # Regular comment that may be removed
    return data.upper()


def _private_helper(text: str) -> str:
    """Private helper that should be removed in public_api_only."""
    tmp = text.strip().lower()
    # Multi-line explanatory comment
    # describing some internal behavior
    return tmp


class PublicClass:
    """Public class exposed to users.

    Contains both public and private members, plus lengthy docstrings.
    """

    def __init__(self, name: str):
        self.name = name
        self._cache: Dict[str, Any] = {}

    def public_method(self, x: int, y: int) -> int:
        """Add two numbers and return the result."""
        return x + y

    def _private_method(self, data: List[str]) -> List[str]:
        """Private method not part of public API."""
        return [d.strip() for d in data]

    @property
    def public_property(self) -> str:
        """Public property."""
        return self.name

    @property
    def _private_property(self) -> Dict[str, Any]:
        """Private property."""
        return self._cache


class _InternalOnly:
    """Private class that should not appear in public API view."""

    def work(self) -> None:
        pass


def huge_processing_pipeline(values: List[int]) -> Tuple[int, int, int]:
    """A long body that can be stripped when budgets are tight."""
    total = 0
    count = 0
    maximum = -10**9
    for v in values:
        count += 1
        total += v
        if v > maximum:
            maximum = v
    return total, count, maximum


def another_long_function():
    """Another long function body to enable stripping heuristics."""
    data = [i * i for i in range(500)]
    s = sum(data)
    m = max(data)
    return s, m


if __name__ == "__main__":
    inst = PublicClass("demo")
    print(public_function("hello"))
    print(inst.public_method(2, 3))
