"""
Utilities for working with language adapters in tests.

Unifies adapter creation, dependency checking, etc.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.markdown import MarkdownAdapter
from lg.stats.tokenizer import default_tokenizer
from .testing_utils import stub_tokenizer


# ===== Python Adapter Utils =====

def make_python_adapter(cfg: PythonCfg) -> PythonAdapter:
    """Python adapter with a pre-configured TokenService stub."""
    adapter = PythonAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    return adapter


def make_python_adapter_real(cfg: PythonCfg) -> PythonAdapter:
    """For tests that verify actual token mathematics."""
    adapter = PythonAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    return adapter


# ===== TypeScript Adapter Utils =====

def make_typescript_adapter(cfg: TypeScriptCfg) -> TypeScriptAdapter:
    """TypeScript adapter with a pre-configured TokenService stub."""
    adapter = TypeScriptAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    return adapter


def make_typescript_adapter_real(cfg: TypeScriptCfg) -> TypeScriptAdapter:
    """For tests that verify actual token mathematics."""
    adapter = TypeScriptAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    return adapter


# ===== Kotlin Adapter Utils =====

def make_kotlin_adapter(cfg):
    """Kotlin adapter with a pre-configured TokenService stub."""
    # Import locally to avoid circular dependencies
    from lg.adapters.kotlin import KotlinAdapter
    adapter = KotlinAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    return adapter


def make_kotlin_adapter_real(cfg):
    """For tests that verify actual token mathematics."""
    from lg.adapters.kotlin import KotlinAdapter
    adapter = KotlinAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    return adapter


# ===== Markdown Adapter Utils =====

def make_markdown_adapter(raw_cfg: Dict[str, Any]) -> MarkdownAdapter:
    """Markdown adapter with pre-configured TokenService."""
    return MarkdownAdapter().bind(raw_cfg, default_tokenizer())


# ===== Tree-sitter Utils =====

def is_tree_sitter_available() -> bool:
    """Check if Tree-sitter is available for testing."""
    try:
        import tree_sitter
        import tree_sitter_python
        import tree_sitter_typescript
        return True
    except ImportError:
        return False


@pytest.fixture
def skip_if_no_tree_sitter():
    """Skip test if Tree-sitter is not available."""
    if not is_tree_sitter_available():
        pytest.skip("Tree-sitter not available")


# ===== Legacy compatibility =====

# For backward compatibility with existing tests
def create_temp_file(tmp_path: Path, filename: str, content: str) -> Path:
    """
    Creates a temporary file with content.

    Compatibility with adapters/conftest.py.
    """
    from .file_utils import write
    return write(tmp_path / filename, content)


__all__ = [
    # Python adapters
    "make_python_adapter", "make_python_adapter_real",
    
    # TypeScript adapters  
    "make_typescript_adapter", "make_typescript_adapter_real",
    
    # Kotlin adapters
    "make_kotlin_adapter", "make_kotlin_adapter_real",
    
    # Markdown adapters
    "make_markdown_adapter",
    
    # Tree-sitter utils
    "is_tree_sitter_available", "skip_if_no_tree_sitter",
    
    # Legacy
    "create_temp_file"
]