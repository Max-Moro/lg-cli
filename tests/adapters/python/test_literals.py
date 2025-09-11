"""
Tests for literal trimming in Python adapter.
"""

from lg.adapters.python import PythonCfg
from lg.adapters.code_model import LiteralConfig
from .conftest import lctx_py, do_literals, assert_golden_match, make_adapter_real


class TestPythonLiteralOptimization:
    """Test literal data optimization for Python code."""

    def test_basic_literal_trimming(self, do_literals):
        """Test basic literal trimming with default settings."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter_real(PythonCfg(literals=literal_config))

        result, meta = adapter.process(lctx_py(do_literals))

        assert_golden_match(result, "literals", "basic_trimming")
