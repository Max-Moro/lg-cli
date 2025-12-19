"""
Tests for literal trimming in Python adapter.
"""

from lg.adapters.python import PythonCfg
from lg.adapters.code_model import LiteralConfig
from .utils import lctx, make_adapter
from ..golden_utils import assert_golden_match


class TestPythonLiteralOptimizationGolden:
    """Test literal data optimization for Python code."""

    def test_basic_literal_trimming_budget_10(self, do_literals):
        """Test basic literal trimming with 10 tokens budget."""
        literal_config = LiteralConfig(max_tokens=10)

        adapter = make_adapter(PythonCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("python.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_10")

    def test_basic_literal_trimming_budget_20(self, do_literals):
        """Test basic literal trimming with 20 tokens budget."""
        literal_config = LiteralConfig(max_tokens=20)

        adapter = make_adapter(PythonCfg(literals=literal_config))

        result, meta = adapter.process(lctx(do_literals))

        assert meta.get("python.removed.literal", 0) > 0

        assert_golden_match(result, "literals", "max_tokens_20")
