"""
Shared fixtures for Rust adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_function_bodies():
    """Sample Rust code for testing function body optimization."""
    return load_sample_code("function_bodies", language="rust")


@pytest.fixture
def do_comments():
    """Sample Rust code for testing comment optimization."""
    return load_sample_code("comments", language="rust")


@pytest.fixture
def do_literals():
    """Sample Rust code for testing literal optimization."""
    return load_sample_code("literals", language="rust")


@pytest.fixture
def do_imports():
    """Sample Rust code for testing import optimization."""
    return load_sample_code("imports", language="rust")


@pytest.fixture
def do_public_api():
    """Sample Rust code for testing public API filtering."""
    return load_sample_code("public_api", language="rust")


@pytest.fixture
def do_complex():
    """Sample Rust code for testing complex combined optimization."""
    return load_sample_code("complex", language="rust")
