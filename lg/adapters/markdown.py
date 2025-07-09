from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lg.adapters.base import BaseAdapter


@dataclass
class LangMarkdown:
    """
    Конфиг для MarkdownAdapter: максимальный уровень заголовков.
    Если None — нормализация заголовков отключена.
    """
    max_heading_level: int | None = None


@BaseAdapter.register
class MarkdownAdapter(BaseAdapter):
    """
    Адаптер для Markdown (.md) файлов.
    Реализует нормализацию заголовков.
    """
    name = "markdown"
    extensions = {".md"}
    config_cls = LangMarkdown

    def process(self, text: str, cfg: LangMarkdown, group_size: int, fence_enabled: bool) -> str:
        """
        Нормализует уровни заголовков:
          1) Если group_size == 1 и первая строка — "# ...", удаляем её.
          2) Если cfg.max_heading_level задан, сдвигаем все заголовки так, чтобы
             минимальный уровень стал равен max_heading_level.
        """
        import re

        if cfg.max_heading_level is None:
            return text

        lines = text.splitlines()
        # Шаг 1: если группа из одного файла — убрать top-level "# "
        if group_size == 1 and lines and re.match(r"^#\s", lines[0]):
            lines = lines[1:]

        # Собираем все уровни заголовков
        levels = [len(m.group(1)) for line in lines if (m := re.match(r"^(#+)\s", line))]
        if not levels:
            return "\n".join(lines)

        min_lvl = min(levels)
        shift = cfg.max_heading_level - min_lvl

        out: list[str] = []
        for line in lines:
            m = re.match(r"^(#+)\s", line)
            if m:
                hashes = "#" * (len(m.group(1)) + shift)
                rest = line[m.end():]
                out.append(f"{hashes} {rest}")
            else:
                out.append(line)

        return "\n".join(out)