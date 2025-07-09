import os
import sys
from pathlib import Path

import pytest

from lg.context import ContextTemplate, generate_context


@pytest.fixture(autouse=True)
def patch_generate(monkeypatch):
    """
    Заменяем реальный generate_listing, чтобы выводить:
      - для секции с section_name != 'empty': LISTING[<section_name>]
      - для 'empty' — ничего (эмулируем пустой листинг)
    """
    import lg.context as ctx_mod

    def fake_generate_listing(root, cfg, mode, list_only=False):
        name = getattr(cfg, "section_name", None)
        if name and name != "empty":
            sys.stdout.write(f"LISTING[{name}]")
        # для 'empty' — ничего

    monkeypatch.setattr(ctx_mod, "generate_listing", fake_generate_listing)


def write_template(tmp_path: Path, context_name: str, content: str):
    """
    Создаёт файл шаблона:
      <tmp_path>/lg-cfg/contexts/{context_name}.tmpl.md
    """
    tmpl_dir = tmp_path / "lg-cfg" / "contexts"
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    tmpl_file = tmpl_dir / f"{context_name}.tmpl.md"
    tmpl_file.write_text(content, encoding="utf-8")


class DummyCfg:
    def __init__(self, section_name: str):
        self.section_name = section_name


def test_context_template_allows_hyphens():
    t = ContextTemplate("Hello ${foo-bar} and ${baz_123}")
    result = t.substitute({"foo-bar": "X", "baz_123": "Y"})
    assert result == "Hello X and Y"


def test_generate_context_success(tmp_path: Path, capsys):
    # Подготавливаем шаблон с двумя плейсхолдерами
    write_template(tmp_path, "ctx", "A: ${docs}\nB: ${empty}")

    # Переходим в tmp_path
    os.chdir(tmp_path)

    # Готовим маппинг configs
    configs = {
        "docs": DummyCfg("docs"),
        "empty": DummyCfg("empty"),
    }

    # Вызываем
    generate_context("ctx", configs)

    out = capsys.readouterr().out
    # Для docs будет LISTING[docs], для empty — пусто → заменяется на *(файлы отсутствуют)*
    assert "A: LISTING[docs]" in out
    assert "B: *(файлы отсутствуют)*" in out


def test_missing_template_raises(tmp_path: Path):
    # Не создаём файл шаблона
    os.chdir(tmp_path)
    with pytest.raises(RuntimeError) as ei:
        generate_context("ctx", {})
    assert "Template not found" in str(ei.value)


def test_unknown_section_raises(tmp_path: Path):
    # Шаблон с плейсхолдером ${unknown}
    write_template(tmp_path, "ctx", "X: ${unknown}")
    os.chdir(tmp_path)

    configs = {"docs": DummyCfg("docs")}
    with pytest.raises(RuntimeError) as ei:
        generate_context("ctx", configs)
    msg = str(ei.value)
    assert "Section 'unknown' not in configs mapping" in msg
