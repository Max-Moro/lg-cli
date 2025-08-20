from pathlib import Path
import textwrap
import pytest

from lg.config import load_config, list_sections, SCHEMA_VERSION


# ========= Тесты, использующие фикстуру tmpproj (см. tests/conftest.py) =========

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


def test_load_config_missing(tmp_path: Path):
    """Отсутствие файла конфига приводит к RuntimeError с понятным текстом."""
    with pytest.raises(RuntimeError):
        load_config(tmp_path)
