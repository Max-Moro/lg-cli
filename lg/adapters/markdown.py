from __future__ import annotations

import re
from dataclasses import dataclass

from .base import BaseAdapter
from ..config import EmptyPolicy


@dataclass
class MarkdownCfg:
    """
    Конфиг для MarkdownAdapter: максимальный уровень заголовков.
    Если None — нормализация заголовков отключена.
    """
    empty_policy: EmptyPolicy = "inherit"
    max_heading_level: int | None = None


class MarkdownAdapter(BaseAdapter):
    """
    Адаптер для Markdown (.md) файлов.
    Реализует нормализацию заголовков.
    """
    name = "markdown"
    extensions = {".md"}
    config_cls = MarkdownCfg

    def process(self, text: str, group_size: int, mixed: bool):
        """
        Нормализация:
          • Если group_size == 1 и первая строка — '# ...' → убрать этот H1.
          • Если задан cfg.max_heading_level — сдвинуть уровни всех заголовков
            вне fenced-блоков так, чтобы минимальный уровень стал равен max_heading_level.
        Метаданные:
          • removed_h1: 0|1
          • shifted: bool
        """
        meta = {"removed_h1": 0, "shifted": False}
        cfg: MarkdownCfg = self._cfg
        # Ничего не делаем, если смешанный листинг или нормализация отключена
        if mixed or (cfg and cfg.max_heading_level is None):
            return text, meta

        max_lvl = int(cfg.max_heading_level) if cfg else None
        lines = text.splitlines()

        # 1) Удаляем верхний H1 только если файл одиночный в группе
        if group_size == 1 and lines and re.match(r"^#\s", lines[0]):
            meta["removed_h1"] = 1
            lines = lines[1:]

        if max_lvl is None:
            return "\n".join(lines), meta

        # 2) Один проход для сбора min уровня заголовков (вне fenced)
        in_fence = False
        min_lvl: int | None = None
        fence_pat = re.compile(r"^```")
        head_pat = re.compile(r"^(#+)\s")
        for ln in lines:
            if fence_pat.match(ln):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            m = head_pat.match(ln)
            if m:
                lvl = len(m.group(1))
                min_lvl = lvl if min_lvl is None else min(min_lvl, lvl)

        if min_lvl is None:
            # заголовков нет — просто возвращаем (с учётом возможного снятого H1)
            return "\n".join(lines), meta

        shift = max_lvl - min_lvl
        meta["shifted"] = bool(shift or meta["removed_h1"])

        if shift == 0:
            return "\n".join(lines), meta

        # 3) Применяем сдвиг уровней (вне fenced)
        out: list[str] = []
        in_fence = False
        for ln in lines:
            if fence_pat.match(ln):
                in_fence = not in_fence
                out.append(ln)
                continue
            if in_fence:
                out.append(ln)
                continue
            m = head_pat.match(ln)
            if m:
                new_hashes = "#" * (len(m.group(1)) + shift)
                out.append(f"{new_hashes} {ln[m.end():]}")
            else:
                out.append(ln)

        return "\n".join(out), meta