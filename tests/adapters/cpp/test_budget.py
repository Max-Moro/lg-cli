"""
Golden tests for Budget System — C++ adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.cpp import CppCfg
from .utils import make_adapter, lctx
from ..golden_utils import assert_golden_match


BUDGET_STEPS = [1176, 1144, 647, 559, 539, 496, 451, 321, 243]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_cpp_budget_progression_golden(budget: int, do_complex):
    code = do_complex

    cfg = CppCfg()
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
        language="cpp",
    )


def test_cpp_budget_is_monotonic_shrink(do_complex):
    """Verify that result length decreases as budget tightens."""
    code = do_complex

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = CppCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
