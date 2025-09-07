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
def code_sample():
    """Sample TypeScript code for testing."""
    return load_sample_code("code_sample")


@pytest.fixture
def barrel_file_sample():
    """Sample TypeScript barrel file for testing."""
    return load_sample_code("barrel_file_sample")


@pytest.fixture
def non_barrel_file_sample():
    """Sample TypeScript non-barrel file for testing."""
    return load_sample_code("non_barrel_file_sample")


@pytest.fixture
def config_simple() -> TypeScriptCfg:
    """Simple TypeScript configuration."""
    return TypeScriptCfg(
        public_api_only=True,
        strip_function_bodies=True
    )
