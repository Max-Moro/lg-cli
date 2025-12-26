"""
Shared fixtures for Scala adapter tests.
"""

import pytest
from ..golden_utils import load_sample_code


@pytest.fixture
def do_function_bodies():
    """Sample Scala code for testing function body optimization."""
    return load_sample_code("function_bodies", language="scala")


@pytest.fixture
def do_comments():
    """Sample Scala code for testing comment optimization."""
    return load_sample_code("comments", language="scala")


@pytest.fixture
def do_literals():
    """Sample Scala code for testing literal optimization."""
    return load_sample_code("literals", language="scala")


@pytest.fixture
def do_imports():
    """Sample Scala code for testing import optimization."""
    return load_sample_code("imports", language="scala")


@pytest.fixture
def do_public_api():
    """Sample Scala code for testing public API filtering."""
    return load_sample_code("public_api", language="scala")


@pytest.fixture
def do_complex():
    """Sample Scala code for testing complex combined optimization."""
    return load_sample_code("complex", language="scala")


@pytest.fixture
def do_trivial():
    """package.scala with only type aliases."""
    return load_sample_code("trivial_package", language="scala")


@pytest.fixture
def do_non_trivial():
    """package.scala with function definition."""
    return load_sample_code("non_trivial_package", language="scala")
