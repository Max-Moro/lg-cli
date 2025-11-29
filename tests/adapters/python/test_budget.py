"""
Golden tests for Budget System (per-file token budgeting) — Python adapter.

This test renders the same complex sample with progressively tighter
max_tokens_per_file limits. We assert monotonic shrinkage and snapshot
each stage to goldens to see how BudgetController escalates steps.
"""

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.python import PythonCfg
from .utils import make_adapter_real, lctx
from ..golden_utils import assert_golden_match, load_sample_code


BUDGET_STEPS = [829, 797, 666, 605, 591, 563, 464, 343, 255]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_python_budget_progression_golden(budget: int):
    code = load_sample_code("budget_complex")

    # Configure adapter with only budget varying
    cfg = PythonCfg()
    cfg.budget = BudgetConfig(max_tokens_per_file=budget)
    cfg.placeholders.style = "none"

    adapter = make_adapter_real(cfg)

    result, meta = adapter.process(lctx(code))

    # Basic sanity on budget metrics presence
    assert any(k.endswith(".budget.tokens_before") for k in meta.keys())
    assert any(k.endswith(".budget.tokens_after") for k in meta.keys())

    # Golden snapshot per budget step
    assert_golden_match(
        result,
        optimization_type="budget",
        golden_name=f"complex_budget_{budget}",
        language="python",
    )


def test_python_budget_is_monotonic_shrink():
    """Non-golden functional check: result length should not increase when budget tightens."""
    code = load_sample_code("budget_complex")

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = PythonCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter_real(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
