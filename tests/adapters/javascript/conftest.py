"""
Shared fixtures and utilities for JavaScript adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code  # noqa: F401


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