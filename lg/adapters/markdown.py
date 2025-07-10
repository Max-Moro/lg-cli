from __future__ import annotations

import re
from dataclasses import dataclass

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

    def process(self, text: str, cfg: LangMarkdown, group_size: int, mixed: bool) -> str:
        """
        Нормализует уровни заголовков:
          1) Если group_size == 1 и первая строка — "# ...", удаляем её.
          2) Если cfg.max_heading_level задан, сдвигаем все заголовки так, чтобы
             минимальный уровень стал равен max_heading_level.
        """

        # нормализуем, если не mixed и задан max_heading_level
        if mixed or cfg.max_heading_level is None:
            return text

        lines = text.splitlines()
        # Шаг 1: если группа из одного файла — убрать top-level "# "
        if group_size == 1 and lines and re.match(r"^#\s", lines[0]):
            lines = lines[1:]

        # Собираем уровни заголовков вне fenced-блоков
        levels: list[int] = []
        in_fence = False
        for line in lines:
            if re.match(r"^```", line):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if (m := re.match(r"^(#+)\s", line)):
                levels.append(len(m.group(1)))
        if not levels:
            # нет заголовков для нормализации; возвращаем исходный текст
            return "\n".join(lines)

        min_lvl = min(levels)
        shift = cfg.max_heading_level - min_lvl

        # Применяем сдвиг только вне fenced-блоков
        out: list[str] = []
        in_fence = False
        for line in lines:
            if re.match(r"^```", line):
                in_fence = not in_fence
                out.append(line)
                continue
            if in_fence:
                out.append(line)
                continue
            if (m := re.match(r"^(#+)\s", line)):
                hashes = "#" * (len(m.group(1)) + shift)
                rest = line[m.end():]
                out.append(f"{hashes} {rest}")
            else:
                out.append(line)

        return "\n".join(out)