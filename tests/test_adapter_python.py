from pathlib import Path
from lg.engine import run_render
from lg.types import RunOptions

def test_trivial_init_skipped(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    # Project config and contexts are created by tmpproj fixture (see tests/conftest.py)
    pkg = tmpproj / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("pass\n", encoding="utf-8")

    # Render virtual section context for section all
    text = run_render("sec:all", RunOptions())

    # Trivial __init__.py should be skipped by adapter -> no file marker
    assert "python:pkg/__init__.py" not in text

def test_non_trivial_init_kept(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    pkg = tmpproj / "pkg"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("VERSION = '1.0'\n", encoding="utf-8")

    text = run_render("sec:all", RunOptions())

    # Non-trivial __init__.py should be included in listing -> marker is present
    assert "python:pkg/__init__.py" in text
