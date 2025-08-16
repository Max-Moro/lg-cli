from pathlib import Path
import textwrap
import pytest

from lg_vnext.config import load_config, list_sections, SCHEMA_VERSION


# ========= Тесты, использующие фикстуру tmpproj (см. tests_vnext/conftest.py) =========

def test_load_config_ok(tmpproj: Path):
    """
    Базовая загрузка конфига из tmpproj:
    - корректная schema_version
    - ожидаемые секции
    - выборочные поля в секциях (code_fence, markdown.max_heading_level)
    """
    cfg = load_config(tmpproj)
    assert cfg.schema_version == 6
    assert set(cfg.sections.keys()) == {"all", "docs"}

    # секция all
    assert cfg.sections["all"].code_fence is True
    # секция docs
    assert cfg.sections["docs"].markdown.max_heading_level == 3


def test_list_sections(tmpproj: Path):
    """list_sections() возвращает имена секций из tmpproj в лексикографическом порядке."""
    assert list_sections(tmpproj) == ["all", "docs"]


# ========= Тесты, создающие собственный конфиг на лету =========

def test_schema_version_mismatch(tmp_path: Path) -> None:
    """Некорректная версия схемы даёт читаемую RuntimeError."""
    p = tmp_path / "lg-cfg" / "config.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        textwrap.dedent("""
        schema_version: 999
        all: {}
        """).strip() + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc:
        load_config(tmp_path)
    assert "Unsupported config schema" in str(exc.value)


def test_load_markdown_and_code_fence(tmp_path: Path) -> None:
    """
    Поля code_fence и markdown.max_heading_level загружаются из YAML секции.
    """
    p = tmp_path / "lg-cfg" / "config.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        textwrap.dedent(f"""
        schema_version: {SCHEMA_VERSION}
        all:
          extensions: [".md"]
          code_fence: true
          markdown:
            max_heading_level: 3
        """).strip() + "\n",
        encoding="utf-8",
    )

    cfg = load_config(tmp_path)
    sec = cfg.sections["all"]
    assert sec.code_fence is True
    assert sec.markdown.max_heading_level == 3


def test_load_config_missing(tmp_path: Path):
    """Отсутствие файла конфига приводит к RuntimeError с понятным текстом."""
    with pytest.raises(RuntimeError):
        load_config(tmp_path)
