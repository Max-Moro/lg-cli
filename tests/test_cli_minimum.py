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
    assert data["formatVersion"] == 4
    assert data["context"]["templateName"] == "ctx:a"
