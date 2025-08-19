from pathlib import Path
import textwrap

from lg.engine import run_render
from lg.types import RunOptions


def _rewrite_all_section_exts(root: Path, exts: list[str]) -> None:
    """
    Переписываем конфиг tmpproj так, чтобы секция `all` включала нужные расширения.
    Остальное (docs/markdown/code_fence) оставляем как в фикстуре.
    """
    (root / "lg-cfg" / "config.yaml").write_text(
        textwrap.dedent(f"""
        schema_version: 6
        all:
          extensions: {exts}
          code_fence: true
          markdown:
            max_heading_level: 2
        docs:
          extensions: [".md"]
          code_fence: false
          markdown:
            max_heading_level: 3
        """).strip() + "\n",
        encoding="utf-8",
    )


def test_two_python_files_grouped(tmpproj: Path, monkeypatch):
    """
    Должен получиться один fenced-блок `python` с двумя файлами и маркерами.
    """
    monkeypatch.chdir(tmpproj)
    # Расширения секции all: .py достаточно (по умолчанию уже есть)
    # создаём файлы
    (tmpproj / "foo.py").write_text('print("foo")\n', encoding="utf-8")
    (tmpproj / "bar.py").write_text('print("bar")\n', encoding="utf-8")

    doc = run_render("sec:all", RunOptions(code_fence=True))
    out = doc.text

    assert out.startswith("```python\n")
    assert out.count("```python") == 1
    assert "# —— FILE: foo.py ——" in out
    assert "# —— FILE: bar.py ——" in out
    assert out.strip().endswith("```")


def test_switch_to_toml_starts_new_block(tmpproj: Path, monkeypatch):
    """
    Последовательность языков: python → toml → python.
    При смене языка должны открываться новые fenced-блоки.
    """
    monkeypatch.chdir(tmpproj)
    # Нужны .toml в расширениях секции all
    _rewrite_all_section_exts(tmpproj, [".md", ".py", ".toml"])

    (tmpproj / "foo.py").write_text('print("foo")\n', encoding="utf-8")
    (tmpproj / "config.toml").write_text('key = "value"\n', encoding="utf-8")
    (tmpproj / "bar.py").write_text('print("bar")\n', encoding="utf-8")

    doc = run_render("sec:all", RunOptions(code_fence=True))
    out = doc.text

    # Два отдельных python-блока (до и после toml)
    assert out.count("```python\n") == 2
    # Между ними — toml-блок
    assert "```toml\n" in out
    # первая секция — python
    assert out.lstrip().startswith("```python\n")
    # внутри toml-блока — наш файл
    assert "```toml\n# —— FILE: config.toml ——" in out
    # после — снова python-блок с bar.py
    assert "```python\n# —— FILE: bar.py ——" in out


def test_language_detection_special_files(tmpproj: Path, monkeypatch):
    """
    Спец-имена должны мапиться в корректные языки:
    - pyproject.toml → toml (спец-имя, проходит без .toml в extensions)
    - pom.xml → xml (нужен .xml в extensions секции)
    - Dockerfile → dockerfile (спец-имя)
    - Makefile → make (спец-имя)
    """
    monkeypatch.chdir(tmpproj)
    # Добавим .xml для pom.xml; pyproject.toml/Dockerfile/Makefile пройдут по спец-именам
    _rewrite_all_section_exts(tmpproj, [".md", ".py", ".xml"])

    (tmpproj / "pyproject.toml").write_text('project = "lg"\n', encoding="utf-8")
    (tmpproj / "pom.xml").write_text("<project></project>\n", encoding="utf-8")
    (tmpproj / "Dockerfile").write_text("FROM python:3.8\n", encoding="utf-8")
    (tmpproj / "Makefile").write_text("all:\n\t@echo hi\n", encoding="utf-8")

    doc = run_render("sec:all", RunOptions(code_fence=True))
    out = doc.text

    assert "```toml\n# —— FILE: pyproject.toml ——\n" in out
    assert "```xml\n# —— FILE: pom.xml ——\n" in out
    assert "```dockerfile\n# —— FILE: Dockerfile ——\n" in out
    assert "```make\n# —— FILE: Makefile ——\n" in out
