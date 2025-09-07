"""
Shared fixtures and utilities for TypeScript adapter tests.
"""

import pytest

from lg.adapters.typescript import TypeScriptAdapter, TypeScriptCfg
from tests.conftest import lctx_ts, lctx  # noqa: F401
from ..golden_utils import assert_golden_match, load_sample_code # noqa: F401


@pytest.fixture
def adapter():
    """Basic TypeScript adapter instance."""
    adapter = TypeScriptAdapter()
    adapter._cfg = TypeScriptCfg()
    return adapter


@pytest.fixture
def do_function_bodies():
    """Sample TypeScript code for testing function body optimization."""
    return load_sample_code("function_bodies")


@pytest.fixture
def barrel_file_sample():
    """Sample TypeScript barrel file for testing."""
    return load_sample_code("barrel_file_sample")


@pytest.fixture
def non_barrel_file_sample():
    """Sample TypeScript non-barrel file for testing."""
    return load_sample_code("non_barrel_file_sample")

# TODO начальные фикстуры для других типов оптимизаций и для комплексных прогонов
# - do_comments
# - do_literals
# - do_imports
# - do_public_api
# - do_fields
# - do_complex
