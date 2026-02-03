from lg.protocol import PROTOCOL_VERSION
from .infrastructure import run_cli, jload

def test_cli_list_contexts(tmpproj):
    cp = run_cli(tmpproj, "list", "contexts")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    assert data["contexts"] == ["a", "b"]

def test_cli_list_sections(tmpproj):
    cp = run_cli(tmpproj, "list", "sections")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    # New format returns section objects with name, mode-sets, tag-sets
    sections = data["sections"]
    assert len(sections) == 2
    section_names = [s["name"] for s in sections]
    assert sorted(section_names) == ["all", "docs"]
    # Each section must have mode-sets and tag-sets (may be empty)
    for section in sections:
        assert "name" in section
        assert "mode-sets" in section
        assert "tag-sets" in section

def test_cli_report_json(tmpproj):
    cp = run_cli(tmpproj, "report", "ctx:a")
    assert cp.returncode == 0, cp.stderr
    data = jload(cp.stdout)
    assert data["protocol"] == PROTOCOL_VERSION
    assert data["context"]["templateName"] == "ctx:a"
