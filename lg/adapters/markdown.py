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

    def process(self, text: str, cfg: LangMarkdown) -> str:
        """
        Нормализует уровни заголовков:
          1) Если первая строка — top-level "# ...", удаляем её.
          2) Сдвигаем все заголовки так, чтобы min_level == cfg.max_heading_level.
        """
        import re

        if cfg.max_heading_level is None:
            return text

        lines = text.splitlines()
        # Шаг 1: убрать top-level header, если есть
        if lines and re.match(r"^#\s", lines[0]):
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