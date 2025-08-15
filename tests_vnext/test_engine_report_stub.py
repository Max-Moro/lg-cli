from lg_vnext.engine import run_report
from lg_vnext.types import RunOptions

def test_run_report_returns_valid_pydantic(tmpproj, monkeypatch):
    monkeypatch.chdir(tmpproj)  # ← ключевая строка
    res = run_report("ctx:a", RunOptions())
    assert res.formatVersion == 4
    assert res.scope == "context"
    assert res.model == "o3"
    assert isinstance(res.rendered_text, str)
    assert res.files == []
    assert res.total.tokensProcessed >= 0
    assert res.context.templateName == "ctx:a"
