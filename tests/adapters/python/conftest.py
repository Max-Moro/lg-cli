"""
Shared fixtures and utilities for Python adapter tests.
"""

import pytest

from lg.adapters.python import PythonCfg
from tests.infrastructure import lctx_py, lctx  # noqa: F401
from ..golden_utils import assert_golden_match, load_sample_code  # noqa: F401

# Imports from unified infrastructure
from tests.infrastructure.adapter_utils import make_python_adapter, make_python_adapter_real


# For backward compatibility
def make_adapter(cfg: PythonCfg):
    """Python adapter with preset TokenService stub."""
    return make_python_adapter(cfg)

def make_adapter_real(cfg: PythonCfg):
    """If tests check real token mathematics."""
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
