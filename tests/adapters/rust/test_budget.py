"""
Golden tests for Budget System — Rust adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.langs.rust import RustCfg
from .utils import make_adapter, lctx
from ..golden_utils import assert_golden_match


BUDGET_STEPS = [773, 729, 682, 604, 590, 508, 243, 148, 81]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_rust_budget_progression_golden(budget: int, do_complex):
    code = do_complex

    cfg = RustCfg()
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
        language="rust",
    )


def test_rust_budget_is_monotonic_shrink(do_complex):
    """Verify that result length decreases as budget tightens."""
    code = do_complex

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = RustCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
