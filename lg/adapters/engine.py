from __future__ import annotations

from pathlib import Path
from typing import List

from lg.cache.fs_cache import Cache
from lg.io.fs import read_text
from lg.types import Plan, ProcessedBlob
from .registry import get_adapter_for_path


def process_groups(plan: Plan, run_ctx) -> List[ProcessedBlob]:
    """
    План групп → список ProcessedBlob с учётом:
      • эвристик should_skip()
      • кэша processed (reused) или свежей обработки
      • подготовленных ключей raw-токенов (для будущей статистики)
    """
    cache: Cache = run_ctx.cache
    out: List[ProcessedBlob] = []
    # Кэш «связанных» (bound) адаптеров по (adapter_name, cfg_dict_immutable)
    bound_cache: dict[tuple[str, tuple[tuple[str, object], ...]], object] = {}

    for grp in plan.groups:
        group_size = len(grp.entries)
        for e in grp.entries:
            fp: Path = e.abs_path
            adapter_cls = get_adapter_for_path(fp)  # ← КЛАСС адаптера (лениво)
            # сырой конфиг адаптера из секции и биндинг к экземпляру (лениво + кэш)
            sec_cfg = run_ctx.config.sections[e.section]
            raw_cfg: dict | None = sec_cfg.adapters.get(adapter_cls.name)
            cfg_key = tuple(sorted((raw_cfg or {}).items()))
            bkey = (adapter_cls.name, cfg_key)
            adapter = bound_cache.get(bkey)
            if adapter is None:
                adapter = adapter_cls.bind(raw_cfg)
                bound_cache[bkey] = adapter

            raw_text = read_text(fp)

            # Эвристики пропуска на уровне адаптера (пустые уже отфильтрованы в Manifest)
            if adapter.name != "base" and adapter.should_skip(fp, raw_text):
                continue

            # ключи кэша
            k_proc, p_proc = cache.build_processed_key(
                abs_path=fp,
                adapter_name=adapter.name,
                adapter_cfg=raw_cfg,
                group_size=group_size,
                mixed=bool(grp.mixed),
            )
            k_raw, p_raw = cache.build_raw_tokens_key(abs_path=fp)

            # попытка взять processed из кэша
            cached = cache.get_processed(p_proc)
            if cached and "processed_text" in cached:
                processed_text = cached["processed_text"]
                meta = cached.get("meta", {}) or {}
            else:
                processed_text, meta = adapter.process(raw_text, group_size, bool(grp.mixed))
                cache.put_processed(p_proc, processed_text=processed_text, meta=meta)

            out.append(ProcessedBlob(
                abs_path=fp,
                rel_path=e.rel_path,
                size_bytes=fp.stat().st_size if fp.exists() else len(raw_text.encode("utf-8", "ignore")),
                processed_text=processed_text.rstrip("\n") + "\n",
                meta=meta,
                raw_text=raw_text,
                cache_key_processed=k_proc,
                cache_key_raw=k_raw,
            ))

    # стабильный порядок: по rel_path
    out.sort(key=lambda b: b.rel_path)
    return out
