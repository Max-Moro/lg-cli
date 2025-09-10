"""
Shared fixtures and utilities for Python adapter tests.
"""

import pytest

from lg.adapters.python import PythonAdapter, PythonCfg
from tests.conftest import lctx_py, lctx, token_service  # noqa: F401
from ..golden_utils import assert_golden_match, load_sample_code # noqa: F401


@pytest.fixture
def adapter(token_service):
    """Python adapter с предустановленным TokenService."""
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg()
    adapter.token_service = token_service
    return adapter


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
