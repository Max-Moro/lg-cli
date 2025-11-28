"""
Shared fixtures and utilities for JavaScript adapter tests.
"""

import pytest

from lg.adapters.javascript import JavaScriptCfg
from tests.infrastructure import lctx  # noqa: F401
from ..golden_utils import assert_golden_match, load_sample_code  # noqa: F401

# Imports from unified infrastructure
from tests.infrastructure.adapter_utils import make_javascript_adapter, make_javascript_adapter_real


# For backward compatibility
def make_adapter(cfg: JavaScriptCfg):
    """JavaScript adapter with preset TokenService stub."""
    return make_javascript_adapter(cfg)

def make_adapter_real(cfg: JavaScriptCfg):
    """If tests check real token mathematics."""
    return make_javascript_adapter_real(cfg)

@pytest.fixture
def do_function_bodies():
    """Sample JavaScript code for testing function body optimization."""
    return load_sample_code("function_bodies")


@pytest.fixture
def do_comments():
    """Sample JavaScript code for testing comment optimization."""
    return load_sample_code("comments")


@pytest.fixture
def do_literals():
    """Sample JavaScript code for testing literal optimization."""
    return load_sample_code("literals")


@pytest.fixture
def do_imports():
    """Sample JavaScript code for testing import optimization."""
    return load_sample_code("imports")


@pytest.fixture
def do_public_api():
    """Sample JavaScript code for testing public API filtering."""
    return load_sample_code("public_api")


@pytest.fixture
def do_complex():
    """Sample JavaScript code for testing complex combined optimization."""
    return load_sample_code("complex")


@pytest.fixture
def lctx_js(lctx):
    """JavaScript-specific lightweight context factory."""
    def _lctx_js(code: str):
        from pathlib import Path
        return lctx(code, Path("test.js"))
    return _lctx_js
