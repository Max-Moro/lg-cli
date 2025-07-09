from __future__ import annotations

import sys
from io import StringIO
from pathlib import Path
from string import Template as _BaseTemplate

from lg.config import list_sections, load_config
from lg.core.generator import generate_listing


class ContextTemplate(_BaseTemplate):
    """
    Расширяем стандартный Template, чтобы в именах плейсхолдеров разрешались
    буквы, цифры, подчёркивания и дефисы (например: core-model-src).
    """
    idpattern = r'[A-Za-z0-9_-]+'

def generate_context(context_name: str, list_only: bool = False) -> None:
    """
    Составляет и выводит на stdout итоговый промт, подставляя
    в шаблон lg-cfg/contexts/{context_name}.tmpl.md листинги (или списки путей)
    из lg-cfg/config.yaml.
    """
    cwd = Path.cwd()
    cfg_dir = cwd / "lg-cfg"
    cfg_path = cfg_dir / "config.yaml"
    tmpl_path = cfg_dir / "contexts" / f"{context_name}.tmpl.md"

    # Проверяем наличие конфигурации и шаблона
    if not cfg_path.is_file():
        raise RuntimeError(f"Config file not found: {cfg_path}")
    if not tmpl_path.is_file():
        raise RuntimeError(f"Template not found: {tmpl_path}")

    # Загружаем шаблон
    text = tmpl_path.read_text(encoding="utf-8")
    template = ContextTemplate(text)

    # Находим все плейсхолдеры ${…}: и named, и braced
    placeholders: set[str] = set()
    for esc, name, braced, invalid in template.pattern.findall(text):
        if name:
            placeholders.add(name)
        elif braced:
            placeholders.add(braced)

    # Доступные секции из конфига
    available = list_sections(cfg_path)

    # Для каждой секции генерируем листинг
    mapping: dict[str, str] = {}
    for section in placeholders:
        if section not in available:
            raise RuntimeError(
                f"Section '{section}' not found in config. "
                f"Available: {', '.join(available)}"
            )

        # Загружаем dataclass-конфиг для этой секции
        cfg = load_config(cfg_path, section)

        # Перехватываем вывод generate_listing в буфер
        buf = StringIO()
        stdout_orig = sys.stdout
        sys.stdout = buf
        try:
            # всегда режим all; list_only управляется флагом
            generate_listing(
                root=cwd,
                cfg=cfg,
                mode="all",
                list_only=list_only,
            )
        finally:
            sys.stdout = stdout_orig

        content = buf.getvalue().strip()
        if not content:
            content = "*(файлы отсутствуют)*"

        mapping[section] = content

    # Подставляем и выводим результат
    # .substitute выбросит KeyError, если в шаблоне есть лишние ${…}
    result = template.substitute(mapping)
    print(result)