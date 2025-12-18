"""
Golden tests for Budget System — JavaScript adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

from __future__ import annotations

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.javascript import JavaScriptCfg
from .utils import make_adapter_real, lctx
from ..golden_utils import assert_golden_match, load_sample_code


# Budget steps for progression testing
BUDGET_STEPS = [598, 564, 517, 443, 420, 356, 250, 179, 99]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_javascript_budget_progression_golden(budget: int):
    code = load_sample_code("budget_complex")

    cfg = JavaScriptCfg()
    cfg.budget = BudgetConfig(max_tokens_per_file=budget)
    cfg.placeholders.style = "none"

    adapter = make_adapter_real(cfg)
    result, meta = adapter.process(lctx(code))

    assert any(k.endswith(".budget.tokens_before") for k in meta.keys())
    assert any(k.endswith(".budget.tokens_after") for k in meta.keys())

    assert_golden_match(
        result,
        optimization_type="budget",
        golden_name=f"complex_budget_{budget}",
        language="javascript",
    )


def test_javascript_budget_is_monotonic_shrink():
    """Verify that result length decreases as budget tightens."""
    code = load_sample_code("budget_complex")

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = JavaScriptCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter_real(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
