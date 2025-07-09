from __future__ import annotations

import sys
from pathlib import Path
from string import Template as _BaseTemplate
from io import StringIO

from lg.config import DEFAULT_CONFIG_DIR
from lg.core.generator import generate_listing


class ContextTemplate(_BaseTemplate):
    """
    Расширяем стандартный Template, чтобы в именах плейсхолдеров
    разрешались буквы, цифры, подчёркивания и дефисы (например: core-model-src).
    """
    idpattern = r'[A-Za-z0-9_-]+'


def generate_context(
    context_name: str,
    configs: dict[str, object],
    list_only: bool = False,
) -> None:
    """
    Собирает и выводит готовый промт по шаблону contexts/{context_name}.tmpl.md,
    подставляя в каждый плейсхолдер ${section} результат работы generate_listing:

      - context_name: имя файла шаблона без расширения
      - configs: маппинг section → Config (загруженный в CLI)
      - list_only: если True, передаём в генератор mode=all, list_only=True

    Ошибки:
      - если шаблон не найден — RuntimeError
      - если в шаблоне есть плейсхолдер без соответствующей секции в configs — RuntimeError
    """
    # Папка с шаблонами: <cwd>/lg-cfg/contexts/
    root = Path.cwd()
    tmpl_path = root / DEFAULT_CONFIG_DIR / "contexts" / f"{context_name}.tmpl.md"
    if not tmpl_path.is_file():
        raise RuntimeError(f"Template not found: {tmpl_path}")

    # Читаем шаблон и создаём ContextTemplate
    text = tmpl_path.read_text(encoding="utf-8")
    template = ContextTemplate(text)

    # Собираем все плейсхолдеры ${...}: и named, и braced
    placeholders: set[str] = set()
    for esc, name, braced, invalid in template.pattern.findall(text):
        if name:
            placeholders.add(name)
        elif braced:
            placeholders.add(braced)

    # Для каждого плейсхолдера подготавливаем листинг
    mapping: dict[str, str] = {}
    for section in placeholders:
        if section not in configs:
            available = ", ".join(sorted(configs.keys()))
            raise RuntimeError(
                f"Section '{section}' not in configs mapping "
                f"(available: {available})"
            )

        cfg = configs[section]

        # Захватываем вывод generate_listing в буфер
        buf = StringIO()
        stdout_orig = sys.stdout
        sys.stdout = buf
        try:
            generate_listing(
                root=root,
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

    # Подставляем готовые блоки в шаблон; KeyError при лишних ${}
    result = template.substitute(mapping)
    sys.stdout.write(result)
