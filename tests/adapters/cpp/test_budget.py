"""
Golden tests for Budget System — C++ adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.cpp import CppCfg
from .utils import make_adapter_real, lctx
from ..golden_utils import assert_golden_match, load_sample_code


BUDGET_STEPS = [650, 600, 530, 470, 440, 400, 360, 280, 200]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_cpp_budget_progression_golden(budget: int):
    code = load_sample_code("budget_complex", language="cpp")

    cfg = CppCfg()
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
        language="cpp",
    )


def test_cpp_budget_is_monotonic_shrink():
    """Verify that result length decreases as budget tightens."""
    code = load_sample_code("budget_complex", language="cpp")

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = CppCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter_real(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
