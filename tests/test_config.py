from pathlib import Path
import pytest

from lg.config import load_config, list_sections


# ========= Тесты, использующие фикстуру tmpproj (см. tests/conftest.py) =========

def test_list_sections(tmpproj: Path):
    """list_sections() возвращает имена секций из tmpproj в лексикографическом порядке."""
    assert list_sections(tmpproj) == ["all", "docs"]


# ========= Тесты, создающие собственный конфиг на лету =========

def test_load_config_missing(tmp_path: Path):
    """Отсутствие файла конфига приводит к RuntimeError с понятным текстом."""
    with pytest.raises(RuntimeError):
        load_config(tmp_path)
