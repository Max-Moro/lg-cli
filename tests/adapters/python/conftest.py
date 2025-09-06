"""
Shared fixtures and utilities for Python adapter tests.
"""

import pytest
from pathlib import Path

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.code_model import FunctionBodyConfig, CommentConfig, ImportConfig, LiteralConfig, FieldConfig
from tests.conftest import lctx_py


@pytest.fixture
def python_adapter():
    """Basic Python adapter instance."""
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg()
    return adapter


@pytest.fixture
def python_code_sample():
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
def python_config_simple() -> PythonCfg:
    """Simple Python configuration."""
    return PythonCfg(
        strip_function_bodies=True,
        comment_policy="keep_doc"
    )


@pytest.fixture
def python_config_advanced() -> PythonCfg:
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


def create_python_context(raw_text: str, group_size: int = 1, mixed: bool = False):
    """Helper to create Python LightweightContext."""
    return lctx_py(raw_text=raw_text, group_size=group_size, mixed=mixed)


def assert_golden_match(result: str, golden_file: Path, update_golden: bool = False):
    """
    Assert that result matches golden file content.
    
    Args:
        result: Actual result string
        golden_file: Path to golden file
        update_golden: If True, update golden file with result
    """
    if update_golden or not golden_file.exists():
        golden_file.parent.mkdir(parents=True, exist_ok=True)
        golden_file.write_text(result, encoding='utf-8')
        if update_golden:
            pytest.skip(f"Updated golden file: {golden_file}")
    
    expected = golden_file.read_text(encoding='utf-8')
    assert result == expected, f"Result doesn't match golden file: {golden_file}"
