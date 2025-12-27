"""
Golden tests for Budget System — JavaScript adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

from __future__ import annotations

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.langs.javascript import JavaScriptCfg
from .utils import make_adapter, lctx
from ..golden_utils import assert_golden_match


# Budget steps for progression testing
BUDGET_STEPS = [598, 557, 425, 368, 345, 268, 207, 76]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_javascript_budget_progression_golden(budget: int, do_complex):
    code = do_complex

    cfg = JavaScriptCfg()
    cfg.budget = BudgetConfig(max_tokens_per_file=budget)
    cfg.placeholders.style = "none"

    adapter = make_adapter(cfg)
    result, meta = adapter.process(lctx(code))

    assert any(k.endswith(".budget.tokens_before") for k in meta.keys())
    assert any(k.endswith(".budget.tokens_after") for k in meta.keys())

    assert_golden_match(
        result,
        optimization_type="budget",
        golden_name=f"complex_budget_{budget}",
        language="javascript",
    )


def test_javascript_budget_is_monotonic_shrink(do_complex):
    """Verify that result length decreases as budget tightens."""
    code = do_complex

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = JavaScriptCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
