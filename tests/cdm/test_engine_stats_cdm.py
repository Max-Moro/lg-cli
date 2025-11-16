from __future__ import annotations

import os
from pathlib import Path

from lg.engine import run_report
from lg.types import RunOptions


def test_run_report_end_to_end_with_cdm(monorepo: Path):
    """
    End-to-end test: run_report on ctx:a.
      • sectionsUsed — canonical keys with correct multiplicity
      • totals — reasonable invariants
      • files[] — contains paths from both sections
    """
    old = os.getcwd()
    os.chdir(monorepo)
    try:
        result = run_report("ctx:a", RunOptions())
    finally:
        os.chdir(old)

    # Context block
    assert result.context is not None
    assert result.context.templateName == "ctx:a"
    # Canonical section keys and multiplicity
    su = result.context.sectionsUsed
    assert su.get("sec@packages/svc-a:a") == 2
    assert su.get("sec@apps/web:web-api") == 1

    # Totals
    t = result.total
    assert t.tokensProcessed > 0
    # Processed text may be larger than original due to placeholders
    # This is normal behavior for language adapters with placeholders
    assert t.tokensRaw > 0  # just verify there are raw tokens
    assert t.renderedTokens is not None and t.renderedTokens >= 0
    # Final document not smaller than pipeline
    assert result.context.finalRenderedTokens is not None
    assert result.context.finalRenderedTokens >= t.renderedTokens
    # Template overhead — non-negative
    assert result.context.templateOverheadPct is not None
    assert result.context.templateOverheadPct >= 0.0

    # Files — at least one from svc-a and one from web
    paths = [f.path for f in result.files]
    assert any(p.startswith("packages/svc-a/") for p in paths)
    assert any(p.startswith("apps/web/") for p in paths)
