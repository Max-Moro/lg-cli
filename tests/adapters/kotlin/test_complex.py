"""
Golden test for maximum aggressive optimization — Kotlin adapter.

This test applies all available optimizations simultaneously without using
the budget system. It provides a quick visual assessment of what the output
looks like when all optimizations are enabled at their most aggressive settings.
"""

from lg.adapters.code_model import (
    ImportConfig,
    LiteralConfig,
    CommentConfig,
    FunctionBodyConfig,
)
from lg.adapters.langs.kotlin import KotlinCfg
from .utils import make_adapter, lctx
from ..golden_utils import assert_golden_match


def test_kotlin_maximum_optimization(do_complex):
    """Apply all optimizations at maximum aggressiveness."""

    # Configure adapter with all optimizations enabled
    cfg = KotlinCfg()
    cfg.public_api_only = True
    cfg.strip_function_bodies = FunctionBodyConfig(policy="strip_all")
    cfg.comment_policy = CommentConfig(policy="keep_first_sentence")
    cfg.imports = ImportConfig(policy="strip_all")
    cfg.literals = LiteralConfig(max_tokens=32)

    adapter = make_adapter(cfg)
    result, _ = adapter.process(lctx(do_complex))

    # Golden snapshot for maximum optimization
    assert_golden_match(
        result,
        optimization_type="complex",
        golden_name="max_optimization",
        language="kotlin",
    )
