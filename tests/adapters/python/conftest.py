"""
Shared fixtures and utilities for Python adapter tests.
"""

import pytest

from lg.adapters.python import PythonCfg
from tests.conftest import lctx_py, lctx  # noqa: F401
from tests.infrastructure.testing_utils import stub_tokenizer
from ..golden_utils import assert_golden_match, load_sample_code  # noqa: F401

# Импорт из унифицированной инфраструктуры
from tests.infrastructure.adapter_utils import make_python_adapter, make_python_adapter_real


# Для обратной совместимости
def make_adapter(cfg: PythonCfg):
    """Python adapter с предустановленной заглушкой TokenService."""
    return make_python_adapter(cfg)

def make_adapter_real(cfg: PythonCfg):
    """Если тесты проверяют реальную математику по токенам."""
    return make_python_adapter_real(cfg)

@pytest.fixture
def do_function_bodies():
    """Sample Python code for testing function body optimization."""
    return load_sample_code("function_bodies")


@pytest.fixture
def do_comments():
    """Sample Python code for testing comment optimization."""
    return load_sample_code("comments")


@pytest.fixture
def do_literals():
    """Sample Python code for testing literal optimization."""
    return load_sample_code("literals")


@pytest.fixture
def do_imports():
    """Sample Python code for testing import optimization."""
    return load_sample_code("imports")


@pytest.fixture
def do_public_api():
    """Sample Python code for testing public API filtering."""
    return load_sample_code("public_api")


@pytest.fixture
def do_fields():
    """Sample Python code for testing field optimization."""
    return load_sample_code("fields")


@pytest.fixture
def do_complex():
    """Sample Python code for testing complex combined optimization."""
    return load_sample_code("complex")
