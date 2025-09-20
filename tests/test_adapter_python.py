from pathlib import Path
from lg.engine import run_render
from lg.types import RunOptions

def test_trivial_init_skipped(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    # Проектный конфиг и контексты создает фикстура tmpproj (см. tests/conftest.py)
    pkg = tmpproj / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("pass\n", encoding="utf-8")

    # Рендерируем виртуальный контекст секции all
    text = run_render("sec:all", RunOptions())

    # Тривиальный __init__.py должен быть пропущен адаптером → маркера файла нет
    assert "# —— FILE: pkg/__init__.py ——" not in text

def test_non_trivial_init_kept(tmpproj: Path, monkeypatch):
    monkeypatch.chdir(tmpproj)
    pkg = tmpproj / "pkg"
    pkg.mkdir(exist_ok=True)
    (pkg / "__init__.py").write_text("VERSION = '1.0'\n", encoding="utf-8")

    text = run_render("sec:all", RunOptions())

    # Нетривиальный __init__.py должен попасть в листинг → маркер присутствует
    assert "# —— FILE: pkg/__init__.py ——" in text
