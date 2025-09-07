"""
Shared fixtures and utilities for Python adapter tests.
"""

import pytest

from lg.adapters.python import PythonAdapter, PythonCfg
from tests.conftest import lctx_py, lctx  # noqa: F401
from ..golden_utils import assert_golden_match, load_sample_code # noqa: F401


@pytest.fixture
def adapter():
    """Basic Python adapter instance."""
    adapter = PythonAdapter()
    adapter._cfg = PythonCfg()
    return adapter


@pytest.fixture
def do_function_bodies():
    """Sample Python code for testing function body optimization."""
    return load_sample_code("function_bodies")

# TODO начальные фикстуры для других типов оптимизаций и для комплексных прогонов
# - do_comments
# - do_literals
# - do_imports
# - do_public_api
# - do_fields
# - do_complex
