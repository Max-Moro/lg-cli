"""
Shared fixtures for Java adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_function_bodies():
    """Sample Java code for testing function body optimization."""
    return load_sample_code("function_bodies", language="java")


@pytest.fixture
def do_comments():
    """Sample Java code for testing comment optimization."""
    return load_sample_code("comments", language="java")


@pytest.fixture
def do_literals():
    """Sample Java code for testing literal optimization."""
    return load_sample_code("literals", language="java")


@pytest.fixture
def do_imports():
    """Sample Java code for testing import optimization."""
    return load_sample_code("imports", language="java")


@pytest.fixture
def do_public_api():
    """Sample Java code for testing public API filtering."""
    return load_sample_code("public_api", language="java")


@pytest.fixture
def do_complex():
    """Sample Java code for testing complex combined optimization."""
    return load_sample_code("budget_complex", language="java")
