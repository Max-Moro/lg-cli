"""
Shared fixtures for Go adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_function_bodies():
    """Sample Go code for testing function body optimization."""
    return load_sample_code("function_bodies", language="go")


@pytest.fixture
def do_comments():
    """Sample Go code for testing comment optimization."""
    return load_sample_code("comments", language="go")


@pytest.fixture
def do_literals():
    """Sample Go code for testing literal optimization."""
    return load_sample_code("literals", language="go")


@pytest.fixture
def do_imports():
    """Sample Go code for testing import optimization."""
    return load_sample_code("imports", language="go")


@pytest.fixture
def do_public_api():
    """Sample Go code for testing public API filtering."""
    return load_sample_code("public_api", language="go")


@pytest.fixture
def do_complex():
    """Sample Go code for testing complex combined optimization."""
    return load_sample_code("complex", language="go")
