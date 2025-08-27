from lg.protocol import PROTOCOL_VERSION
from .conftest import run_cli, jload

def test_cli_list_contexts(tmpproj):
    cp = run_cli(tmpproj, "list", "contexts")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    assert data["contexts"] == ["a", "b"]

def test_cli_list_sections(tmpproj):
    cp = run_cli(tmpproj, "list", "sections")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    assert data["sections"] == ["all", "docs"]

def test_cli_report_json(tmpproj):
    cp = run_cli(tmpproj, "report", "ctx:a")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    assert data["protocol"] == PROTOCOL_VERSION
    assert data["context"]["templateName"] == "ctx:a"

def test_cli_list_models_defaults(tmpproj):
    cp = run_cli(tmpproj, "list", "models")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    models = data["models"]
    # Структура объектов
    assert isinstance(models, list) and len(models) > 0
    m0 = models[0]
    assert {"id","label","base","plan","provider","encoder","ctxLimit"} <= set(m0.keys())
    # Должны присутствовать и "o3", и один из комбо "o3 (Pro)"
    ids = {m["id"] for m in models}
    labels = {m["label"] for m in models}
    assert "o3" in ids
    assert any(lbl.startswith("o3 (Pro") for lbl in labels)