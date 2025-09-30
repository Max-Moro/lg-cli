"""
Утилиты для работы с языковыми адаптерами в тестах.

Унифицирует создание адаптеров, проверку зависимостей и т.д.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import pytest

from lg.adapters.python import PythonAdapter, PythonCfg
from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from lg.adapters.markdown import MarkdownAdapter
from lg.stats.tokenizer import default_tokenizer
from tests.conftest import stub_tokenizer


# ===== Python Adapter Utils =====

def make_python_adapter(cfg: PythonCfg) -> PythonAdapter:
    """Python adapter с предустановленной заглушкой TokenService."""
    adapter = PythonAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    return adapter


def make_python_adapter_real(cfg: PythonCfg) -> PythonAdapter:
    """Если тесты проверяют реальную математику по токенам."""
    adapter = PythonAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    return adapter


# ===== TypeScript Adapter Utils =====

def make_typescript_adapter(cfg: TypeScriptCfg) -> TypeScriptAdapter:
    """TypeScript adapter с предустановленной заглушкой TokenService."""
    adapter = TypeScriptAdapter().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    return adapter


def make_typescript_adapter_real(cfg: TypeScriptCfg) -> TypeScriptAdapter:
    """Если тесты проверяют реальную математику по токенам."""
    adapter = TypeScriptAdapter().bind(None, default_tokenizer())
    adapter._cfg = cfg
    return adapter


# ===== Markdown Adapter Utils =====

def make_markdown_adapter(raw_cfg: Dict[str, Any]) -> MarkdownAdapter:
    """Markdown adapter с предустановленным TokenService."""
    return MarkdownAdapter().bind(raw_cfg, default_tokenizer())


# ===== Generic Adapter Utils =====

def make_adapter(adapter_class, cfg):
    """
    Универсальная функция для создания адаптера с заглушкой токенизатора.
    
    Args:
        adapter_class: Класс адаптера (PythonAdapter, TypeScriptAdapter, etc.)
        cfg: Конфигурация адаптера
        
    Returns:
        Настроенный адаптер
    """
    adapter = adapter_class().bind(None, stub_tokenizer())
    adapter._cfg = cfg
    return adapter


def make_adapter_real(adapter_class, cfg):
    """
    Универсальная функция для создания адаптера с реальным токенизатором.
    
    Args:
        adapter_class: Класс адаптера (PythonAdapter, TypeScriptAdapter, etc.)
        cfg: Конфигурация адаптера
        
    Returns:
        Настроенный адаптер
    """
    adapter = adapter_class().bind(None, default_tokenizer())
    adapter._cfg = cfg
    return adapter


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

# Для обратной совместимости с существующими тестами
def create_temp_file(tmp_path: Path, filename: str, content: str) -> Path:
    """
    Создает временный файл с содержимым.
    
    Совместимость с adapters/conftest.py.
    """
    from .file_utils import write
    return write(tmp_path / filename, content)


__all__ = [
    # Python adapters
    "make_python_adapter", "make_python_adapter_real",
    
    # TypeScript adapters  
    "make_typescript_adapter", "make_typescript_adapter_real",
    
    # Markdown adapters
    "make_markdown_adapter",
    
    # Generic adapters
    "make_adapter", "make_adapter_real",
    
    # Tree-sitter utils
    "is_tree_sitter_available", "skip_if_no_tree_sitter",
    
    # Legacy
    "create_temp_file"
]