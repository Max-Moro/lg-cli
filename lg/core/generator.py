from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from .plan import collect_entries, build_plan
from ..config.model import Config


def generate_listing(
    *,
    root: Path,
    cfg: Config,
    mode: str = "all",
    list_only: bool = False,
    _return_stats: bool = False,            # ← внутр. флаг для stats-режима
):
    # 1) общий сбор файлов
    file_entries = collect_entries(root=root, cfg=cfg, mode=mode)
    listed_paths: List[str] = []

    # режим простого списка (путей или данных для stats)
    if list_only:
        if _return_stats:
            return [(e.fp, e.rel_path, e.fp.stat().st_size) for e in file_entries]
        else:
            listing = "\n".join(sorted(e.rel_path for e in file_entries))
            if file_entries:
                listing += "\n"
            sys.stdout.write(listing)
            return

    # 2) строим план группировки
    plan = build_plan(file_entries, cfg)

    # 3) генерация вывода
    out_lines: List[str] = []

    if plan.use_fence:
        for grp in plan.groups:
            group_size = len(grp.entries)
            out_lines.append(f"```{grp.lang}\n")
            for idx, e in enumerate(grp.entries):
                cfg_lang = getattr(cfg, e.adapter.name, None)
                text = e.adapter.process(e.text, cfg_lang, group_size, False)
                text = text.rstrip("\n") + "\n"
                if e.adapter.name != "markdown":
                    out_lines.append(f"# —— FILE: {e.rel_path} ——\n")
                out_lines.append(text)
                if idx < group_size - 1:
                    out_lines.append("\n\n")
            out_lines.append("```\n\n")
    else:
        grp = plan.groups[0] if plan.groups else None
        if grp:
            group_size = len(grp.entries)
            for idx, e in enumerate(grp.entries):
                cfg_lang = getattr(cfg, e.adapter.name, None)
                text = e.adapter.process(e.text, cfg_lang, group_size, grp.mixed)
                text = text.rstrip("\n") + "\n"
                if not (plan.md_only or e.adapter.name == "markdown"):
                    out_lines.append(f"# —— FILE: {e.rel_path} ——\n")
                out_lines.append(text)
                if idx < group_size - 1:
                    out_lines.append("\n\n")

    sys.stdout.write("".join(out_lines))
