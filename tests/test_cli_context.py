from .infrastructure import run_cli

def test_cli_report_missing_context_exits_nonzero(tmpproj):
    # context ctx:missing does not exist -> non-zero exit code, stderr contains error
    cp = run_cli(tmpproj, "report", "ctx:missing")
    assert cp.returncode != 0
    assert "Context template not found" in (cp.stderr or "")

def test_cli_render_section_smoke(tmpproj):
    # section docs exists (see tmpproj fixture), command completes successfully
    cp = run_cli(tmpproj, "render", "sec:docs")
    assert cp.returncode == 0, cp.stderr
    # Don't assert anything specific about content: text depends on project files
    assert isinstance(cp.stdout, str)
    # ensure something was rendered (even an empty string is acceptable)
    assert cp.stdout is not None
