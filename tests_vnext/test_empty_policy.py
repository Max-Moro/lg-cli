import textwrap
from pathlib import Path

from lg_vnext.engine import run_render
from lg_vnext.types import RunOptions


def _write(p: Path, text: str = "") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p

def test_empty_policy_include_overrides_section_skip(tmp_path: Path, monkeypatch):
    """
    Секция запрещает пустые (skip_empty:true), но python.empty_policy: include —
    пустой m.py должен попасть в рендер.
    """
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lg-cfg" / "config.yaml").write_text(
        textwrap.dedent("""
        schema_version: 6
        all:
          extensions: [".py"]
          code_fence: true
          skip_empty: true
          python:
            empty_policy: include
        """).strip() + "\n",
        encoding="utf-8",
    )
    _write(tmp_path / "m.py", "")

    monkeypatch.chdir(tmp_path)
    doc = run_render("sec:all", RunOptions())
    out = doc.text
    assert "# —— FILE: m.py ——" in out  # файл не отфильтрован

def test_empty_policy_exclude_overrides_section_allow(tmp_path: Path, monkeypatch):
    """
    Секция разрешает пустые (skip_empty:false), но markdown.empty_policy: exclude —
    пустой README.md должен быть исключён.
    Добавляем также .py, чтобы документ не был md-only (тогда виден маркер файлов).
    """
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lg-cfg" / "config.yaml").write_text(
        textwrap.dedent("""
        schema_version: 6
        all:
          extensions: [".md", ".py"]
          code_fence: true
          skip_empty: false
          markdown:
            empty_policy: exclude
        """).strip() + "\n",
        encoding="utf-8",
    )
    _write(tmp_path / "README.md", "")     # пустой markdown → должен отфильтроваться
    _write(tmp_path / "x.py", "print('x')\n")

    monkeypatch.chdir(tmp_path)
    doc = run_render("sec:all", RunOptions())
    out = doc.text
    # маркер для README.md отсутствует
    assert "# —— FILE: README.md ——" not in out
    # а .py виден — чтобы убедиться, что рендер прошёл
    assert "# —— FILE: x.py ——" in out

def test_empty_policy_inherit_follows_section(tmp_path: Path, monkeypatch):
    """
    Поведение по умолчанию ('inherit'): следуем секционному флагу skip_empty.
    Секция skip_empty:true → пустой .py отфильтровывается.
    """
    (tmp_path / "lg-cfg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lg-cfg" / "config.yaml").write_text(
        textwrap.dedent("""
        schema_version: 6
        all:
          extensions: [".py"]
          code_fence: true
          skip_empty: true
          python:
            empty_policy: inherit
        """).strip() + "\n",
        encoding="utf-8",
    )
    _write(tmp_path / "m.py", "")  # пустой .py

    monkeypatch.chdir(tmp_path)
    doc = run_render("sec:all", RunOptions())
    out = doc.text
    assert "# —— FILE: m.py ——" not in out
    assert out.strip() == ""
