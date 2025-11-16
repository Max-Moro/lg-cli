"""
Shared fixtures and utilities for Kotlin adapter tests.
"""

import pytest

from lg.adapters.kotlin import KotlinCfg
from tests.infrastructure import lctx, lctx_kt  # noqa: F401
from ..golden_utils import assert_golden_match, load_sample_code  # noqa: F401

# Imports from unified infrastructure
from tests.infrastructure.adapter_utils import make_kotlin_adapter, make_kotlin_adapter_real


# For backward compatibility
def make_adapter(cfg: KotlinCfg):
    """Kotlin adapter with preset TokenService stub."""
    return make_kotlin_adapter(cfg)

def make_adapter_real(cfg: KotlinCfg):
    """If tests check real token mathematics."""
    return make_kotlin_adapter_real(cfg)

@pytest.fixture
def do_function_bodies():
    """Sample Kotlin code for testing function body optimization."""
    return load_sample_code("function_bodies")


@pytest.fixture
def do_comments():
    """Sample Kotlin code for testing comment optimization."""
    return load_sample_code("comments")


@pytest.fixture
def do_literals():
    """Sample Kotlin code for testing literal optimization."""
    return load_sample_code("literals")


@pytest.fixture
def do_imports():
    """Sample Kotlin code for testing import optimization."""
    return load_sample_code("imports")


@pytest.fixture
def do_public_api():
    """Sample Kotlin code for testing public API filtering."""
    return load_sample_code("public_api")


@pytest.fixture
def do_complex():
    """Sample Kotlin code for testing complex combined optimization."""
    return load_sample_code("complex")

