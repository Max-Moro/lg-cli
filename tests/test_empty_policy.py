import textwrap
from pathlib import Path

from lg.engine import run_render
from lg.types import RunOptions
from tests.infrastructure import create_integration_mode_section


def _write(p: Path, text: str = "") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p

def test_empty_policy_include_overrides_section_skip(tmp_path: Path, monkeypatch):
    """
    Section forbids empty files (skip_empty:true), but python.empty_policy: include —
    empty m.py should be included in render.
    """
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    create_integration_mode_section(tmp_path)
    (tmp_path / "lg-cfg" / "sections.yaml").write_text(
        textwrap.dedent("""
        all:
          extends: ["ai-interaction"]
          extensions: [".py"]
          skip_empty: true
          python:
            empty_policy: include
          filters:
            mode: allow
            allow:
              - "/**"
        """).strip() + "\n",
        encoding="utf-8",
    )
    _write(tmp_path / "m.py", "")

    monkeypatch.chdir(tmp_path)
    out = run_render("sec:all", RunOptions())
    assert "python:m.py" in out  # file is not filtered

def test_empty_policy_exclude_overrides_section_allow(tmp_path: Path, monkeypatch):
    """
    Section allows empty files (skip_empty:false), but markdown.empty_policy: exclude —
    empty README.md should be excluded.
    Also add .py so document is not md-only (then file marker is visible).
    """
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    create_integration_mode_section(tmp_path)
    (tmp_path / "lg-cfg" / "sections.yaml").write_text(
        textwrap.dedent("""
        all:
          extends: ["ai-interaction"]
          extensions: [".md", ".py"]
          skip_empty: false
          markdown:
            empty_policy: exclude
          filters:
            mode: allow
            allow:
              - "/**"
        """).strip() + "\n",
        encoding="utf-8",
    )
    _write(tmp_path / "README.md", "")     # empty markdown -> should be filtered
    _write(tmp_path / "x.py", "print('x')\n")

    monkeypatch.chdir(tmp_path)
    out = run_render("sec:all", RunOptions())
    # marker for README.md is missing
    assert "python:README.md" not in out
    # and .py is visible - to ensure render succeeded
    assert "python:x.py" in out

def test_empty_policy_inherit_follows_section(tmp_path: Path, monkeypatch):
    """
    Default behavior ('inherit'): follow section's skip_empty flag.
    Section skip_empty:true -> empty .py is filtered.
    """
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    create_integration_mode_section(tmp_path)
    (tmp_path / "lg-cfg" / "sections.yaml").write_text(
        textwrap.dedent("""
        all:
          extends: ["ai-interaction"]
          extensions: [".py"]
          skip_empty: true
          python:
            empty_policy: inherit
          filters:
            mode: allow
            allow:
              - "/**"
        """).strip() + "\n",
        encoding="utf-8",
    )
    _write(tmp_path / "m.py", "")  # empty .py

    monkeypatch.chdir(tmp_path)
    out = run_render("sec:all", RunOptions())
    assert "python:m.py" not in out
    assert out.strip() == ""
