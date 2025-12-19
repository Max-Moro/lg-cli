"""
Shared fixtures for C++ adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_function_bodies():
    """Sample C++ code for testing function body optimization."""
    return load_sample_code("function_bodies", language="cpp")


@pytest.fixture
def do_comments():
    """Sample C++ code for testing comment optimization."""
    return load_sample_code("comments", language="cpp")


@pytest.fixture
def do_literals():
    """Sample C++ code for testing literal optimization."""
    return load_sample_code("literals", language="cpp")


@pytest.fixture
def do_imports():
    """Sample C++ code for testing include optimization."""
    return load_sample_code("imports", language="cpp")


@pytest.fixture
def do_public_api():
    """Sample C++ code for testing public API filtering."""
    return load_sample_code("public_api", language="cpp")


@pytest.fixture
def do_complex():
    """Sample C++ code for testing complex combined optimization."""
    return load_sample_code("complex", language="cpp")
