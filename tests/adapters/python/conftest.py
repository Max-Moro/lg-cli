"""
Shared fixtures and utilities for Python adapter tests.
"""

import pytest

from lg.adapters.code_model import FunctionBodyConfig, CommentConfig
from lg.adapters.python import PythonAdapter, PythonCfg
from tests.conftest import lctx_py, lctx  # noqa: F401
from ..golden_utils import assert_golden_match  # noqa: F401


@pytest.fixture
def adapter():
    """Basic Python adapter instance."""
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg()
    return adapter


@pytest.fixture
def code_sample():
    """Sample Python code for testing."""
    return '''"""Module docstring."""

import os
import sys
from typing import List, Optional

class Calculator:
    """A simple calculator class."""
    
    def __init__(self, name: str = "default"):
        """Initialize calculator."""
        self.name = name
        self.history = []
    
    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
    
    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"multiply({a}, {b}) = {result}")
        return result
    
    def get_history(self) -> List[str]:
        """Get calculation history."""
        return self.history.copy()

def main():
    """Main function."""
    calc = Calculator("test")
    print(calc.add(2, 3))
    print(calc.multiply(4, 5))
    
if __name__ == "__main__":
    main()
'''


@pytest.fixture
def config_simple() -> PythonCfg:
    """Simple Python configuration."""
    return PythonCfg(
        strip_function_bodies=True,
        comment_policy="keep_doc"
    )


@pytest.fixture
def config_advanced() -> PythonCfg:
    """Advanced Python configuration."""
    return PythonCfg(
        strip_function_bodies=FunctionBodyConfig(
            mode="large_only",
            min_lines=3
        ),
        comment_policy=CommentConfig(
            policy="keep_first_sentence",
            max_length=100
        )
    )
