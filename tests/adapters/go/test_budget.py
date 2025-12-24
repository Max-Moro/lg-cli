"""
Golden tests for Budget System — Go adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.langs.go import GoCfg
from .utils import make_adapter, lctx
from ..golden_utils import assert_golden_match


BUDGET_STEPS = [927, 914, 767, 628, 615, 522, 492, 349, 284]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_go_budget_progression_golden(budget: int, do_complex):
    code = do_complex

    cfg = GoCfg()
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
        language="go",
    )


def test_go_budget_is_monotonic_shrink(do_complex):
    """Verify that result length decreases as budget tightens."""
    code = do_complex

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = GoCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
