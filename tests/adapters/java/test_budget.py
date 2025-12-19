"""
Golden tests for Budget System — Java adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.java import JavaCfg
from .utils import make_adapter, lctx
from ..golden_utils import assert_golden_match, load_sample_code


BUDGET_STEPS = [970, 950, 868, 787, 761, 697, 401, 293, 213]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_java_budget_progression_golden(budget: int):
    code = load_sample_code("budget_complex", language="java")

    cfg = JavaCfg()
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
        language="java",
    )


def test_java_budget_is_monotonic_shrink():
    """Verify that result length decreases as budget tightens."""
    code = load_sample_code("budget_complex", language="java")

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = JavaCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
