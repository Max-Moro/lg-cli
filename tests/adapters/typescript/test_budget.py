"""
Golden tests for Budget System — TypeScript adapter.

Run a complex sample through progressively smaller budgets and snapshot each stage.
"""

from __future__ import annotations

import pytest

from lg.adapters.code_model import BudgetConfig
from lg.adapters.typescript import TypeScriptCfg
from .conftest import make_adapter_real
from ..golden_utils import assert_golden_match, load_sample_code
from tests.conftest import lctx_ts


BUDGET_STEPS = [642, 608, 529, 413, 392, 352, 327, 231, 187]


@pytest.mark.parametrize("budget", BUDGET_STEPS)
def test_typescript_budget_progression_golden(budget: int):
    code = load_sample_code("budget_complex")

    cfg = TypeScriptCfg()
    cfg.budget = BudgetConfig(max_tokens_per_file=budget)
    cfg.placeholders.style = "none"

    adapter = make_adapter_real(cfg)
    result, meta = adapter.process(lctx_ts(code))

    assert any(k.endswith(".budget.tokens_before") for k in meta.keys())
    assert any(k.endswith(".budget.tokens_after") for k in meta.keys())

    assert_golden_match(
        result,
        optimization_type="budget",
        golden_name=f"complex_budget_{budget}",
        language="typescript",
    )


def test_typescript_budget_is_monotonic_shrink():
    code = load_sample_code("budget_complex")

    lengths: list[int] = []
    for budget in BUDGET_STEPS:
        cfg = TypeScriptCfg()
        cfg.budget = BudgetConfig(max_tokens_per_file=budget)
        cfg.placeholders.style = "none"
        adapter = make_adapter_real(cfg)
        result, _ = adapter.process(lctx_ts(code))
        lengths.append(len(result))

    for i in range(1, len(lengths)):
        assert lengths[i] < lengths[i - 1], (
            f"Output grew at step {i}: {lengths[i-1]} -> {lengths[i]}"
        )
