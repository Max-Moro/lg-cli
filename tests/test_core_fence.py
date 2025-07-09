import sys
from io import StringIO

import pytest

from lg.config.model import Config, LangPython, LangMarkdown
from lg.core.generator import generate_listing
from lg.filters.model import FilterNode


@pytest.fixture
def cfg(tmp_path):
    # Базовый конфиг, расширяемый в тестах
    cfg = Config()
    # Обрабатываем .py, .toml, .xml и файлы без расширения
    cfg.extensions = [".py", ".toml", ".xml", ""]
    # Не пропускать пустые файлы для тестов
    cfg.skip_empty = False
    cfg.python = LangPython(skip_empty=False)
    cfg.markdown = LangMarkdown(max_heading_level=None)
    # code_fence по умолчанию True
    cfg.code_fence = True
    # Фильтры: default-allow
    cfg.filters = FilterNode(mode="block")
    return cfg

def run_listing(tmp_path, cfg, files):
    # создаём файлы
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    # захватываем вывод
    buf = StringIO()
    old = sys.stdout
    sys.stdout = buf
    try:
        generate_listing(root=tmp_path, cfg=cfg)
    finally:
        sys.stdout = old
    return buf.getvalue()

def test_two_python_files_grouped(tmp_path, cfg):
    files = {
        "foo.py": 'print("foo")\n',
        "bar.py": 'print("bar")\n',
    }
    out = run_listing(tmp_path, cfg, files)
    # Должен быть ровно один блок python с обеими файлами внутри
    assert out.startswith("```python\n")
    assert out.count("```python") == 1
    # Оба маркера файлов внутри
    assert "# —— FILE: foo.py ——" in out
    assert "# —— FILE: bar.py ——" in out
    # После второго файла — закрывающий ```
    assert out.strip().endswith("```")

def test_switch_to_toml_starts_new_block(tmp_path, cfg):
    files = {
        "foo.py": 'print("foo")\n',
        "config.toml": 'key = "value"\n',
        "bar.py": 'print("bar")\n',
    }
    out = run_listing(tmp_path, cfg, files)
    # Должна быть секция python, затем toml, затем python снова
    # Два открытия python-блока
    assert out.count("```python\n") == 2
    # Открытие toml-блока
    assert "```toml\n" in out
    # Правильная последовательность
    # первая строка — python
    assert out.lstrip().startswith("```python\n")
    # потом где-то toml
    assert "```toml\n# —— FILE: config.toml ——" in out
    # потом снова python-файл bar.py
    assert "```python\n# —— FILE: bar.py ——" in out

def test_language_detection_special_files(tmp_path, cfg):
    files = {
        "pyproject.toml": 'project = "lg"\n',
        "pom.xml": '<project></project>\n',
        "Dockerfile": 'FROM python:3.8\n',
        "Makefile": 'all:\n\techo hi\n',
    }
    out = run_listing(tmp_path, cfg, files)
    # Разные блоки для каждого «языка»
    assert "```toml\n# —— FILE: pyproject.toml ——\n" in out
    assert "```xml\n# —— FILE: pom.xml ——\n" in out
    assert "```dockerfile\n# —— FILE: Dockerfile ——\n" in out
    assert "```make\n# —— FILE: Makefile ——\n" in out
