from __future__ import annotations

import sys
from pathlib import Path
from typing import List

from .cache import Cache
from .plan import collect_entries, build_plan
from ..config.model import Config


def generate_listing(
    *,
    root: Path,
    cfg: Config,
    mode: str = "all",
    list_only: bool = False,
    _return_stats: bool = False,            # ← внутр. флаг для stats-режима
    cache: Cache | None = None,
):
    # 1) общий сбор файлов
    file_entries = collect_entries(root=root, cfg=cfg, mode=mode)

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
    cache = cache or Cache(root)

    # 3) генерация вывода
    out_lines: List[str] = []

    if plan.use_fence:
        for grp in plan.groups:
            group_size = len(grp.entries)
            out_lines.append(f"```{grp.lang}\n")
            for idx, e in enumerate(grp.entries):
                from .plan import _process_with_cache
                pr = _process_with_cache(e, cfg, group_size, False, cache)
                text = pr.processed_text
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

                key_hash, key_path = cache.build_key(
                    abs_path=e.fp,
                    adapter_name=e.adapter.name,
                    adapter_cfg=cfg_lang,
                    group_size=group_size,
                    mixed=grp.mixed,
                )
                cached = cache.get_processed(key_hash, key_path)
                if cached and "processed_text" in cached:
                    text = cached["processed_text"]
                else:
                    text = e.adapter.process(e.text, cfg_lang, group_size, grp.mixed)
                    cache.put_processed(key_hash, key_path, processed_text=text)

                text = text.rstrip("\n") + "\n"
                if not (plan.md_only or e.adapter.name == "markdown"):
                    out_lines.append(f"# —— FILE: {e.rel_path} ——\n")
                out_lines.append(text)
                if idx < group_size - 1:
                    out_lines.append("\n\n")

    sys.stdout.write("".join(out_lines))
