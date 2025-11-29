"""
Golden tests for Budget System — Kotlin adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

from __future__ import annotations

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.kotlin import KotlinCfg
from .utils import make_adapter_real, lctx
from ..golden_utils import assert_golden_match, load_sample_code


# Budget steps for progression testing
BUDGET_STEPS = [751, 728, 633, 541, 514, 458, 407, 287, 212]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_kotlin_budget_progression_golden(budget: int):
    code = load_sample_code("budget_complex")

    cfg = KotlinCfg()
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
        language="kotlin",
    )


def test_kotlin_budget_is_monotonic_shrink():
    """Verify that result length decreases as budget tightens."""
    code = load_sample_code("budget_complex")

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = KotlinCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter_real(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )

