"""
Проверяем YAML-загрузчик `lg.config.load_config`:

1. Корректный файл разбирается в объект `Config`,
   поля загружаются и переопределяют дефолты.
2. Несовпадение `schema_version` приводит к понятной ошибке.
"""

from pathlib import Path

import pytest

from lg.config import Config, SCHEMA_VERSION, load_config, DEFAULT_SECTION_NAME


def test_load_valid_yaml(tmp_path: Path) -> None:
    """Конфиг с актуальной схемой парсится без ошибок."""
    cfg_path = tmp_path / "listing_config.yaml"
    cfg_yaml = f"""
schema_version: {SCHEMA_VERSION}
all:
  extensions: [".py", ".md"]
  python:
    skip_empty: false
"""
    cfg_path.write_text(cfg_yaml)

    cfg = load_config(cfg_path, DEFAULT_SECTION_NAME)

    assert isinstance(cfg, Config)
    assert ".md" in cfg.extensions              # пользовательские данные подхватились
    assert cfg.python.skip_empty is False       # и секция Python прошла в dataclass


def test_schema_version_mismatch(tmp_path: Path) -> None:
    """Некорректная версия схемы даёт читаемую RuntimeError."""
    bad_cfg = tmp_path / "listing_config.yaml"
    bad_cfg.write_text(
        """
schema_version: 999
"""
    )

    with pytest.raises(RuntimeError) as exc:
        load_config(bad_cfg, DEFAULT_SECTION_NAME)

    # Сообщение должно ясно указывать на проблему
    assert "Unsupported config schema" in str(exc.value)
