"""
Golden tests for Budget System — TypeScript adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

from __future__ import annotations

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.langs.typescript import TypeScriptCfg
from .utils import make_adapter, lctx
from ..golden_utils import assert_golden_match


BUDGET_STEPS = [642, 608, 560, 481, 460, 393, 365, 269, 189]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_typescript_budget_progression_golden(budget: int, do_complex):
    code = do_complex

    cfg = TypeScriptCfg()
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
        language="typescript",
    )


def test_typescript_budget_is_monotonic_shrink(do_complex):
    code = do_complex

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = TypeScriptCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter(cfg)
        result, _ = adapter.process(lctx(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
