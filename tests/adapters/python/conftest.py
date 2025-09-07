"""
Shared fixtures and utilities for Python adapter tests.
"""

import pytest

from lg.adapters.code_model import FunctionBodyConfig, CommentConfig
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
def code_sample():
    """Sample Python code for testing."""
    return load_sample_code("code_sample")


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
