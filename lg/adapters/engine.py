from __future__ import annotations

from pathlib import Path
from typing import List, Any

from lg.cache.fs_cache import Cache
from lg.io.fs import read_text
from lg.types import ContextPlan, ProcessedBlob
from .registry import get_adapter_for_path
from ..run_context import RunContext


def _freeze_cfg(obj: Any) -> Any:
    """
    Делает объект хэшируемым и детерминированным:
      - dict -> tuple(sorted((key, freeze(value))...))
      - list/tuple -> tuple(freeze(x) for x in obj)
      - set -> tuple(sorted(freeze(x) for x in obj))
      - прочие примитивы оставляем как есть
    """
    if isinstance(obj, dict):
        return tuple((k, _freeze_cfg(v)) for k, v in sorted(obj.items(), key=lambda kv: kv[0]))
    if isinstance(obj, (list, tuple)):
        return tuple(_freeze_cfg(x) for x in obj)
    if isinstance(obj, set):
        return tuple(sorted(_freeze_cfg(x) for x in obj))
    return obj

def process_groups(plan: ContextPlan, run_ctx: RunContext) -> List[ProcessedBlob]:
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

    for sec_plan in plan.sections:
        for grp in sec_plan.groups:
            group_size = len(grp.entries)
            for e in grp.entries:
                fp: Path = e.abs_path
                adapter_cls = get_adapter_for_path(fp)  # ← КЛАСС адаптера (лениво)
                # Базовый (секционный) сырой конфиг Берём из плана секции (адресный lg-cfg)
                sec_raw_cfg: dict | None = (getattr(sec_plan, "adapters_cfg", {}) or {}).get(adapter_cls.name)
                # адресные оверрайды по пути
                override_cfg: dict | None = (e.adapter_overrides or {}).get(adapter_cls.name)
                # объединяем (секционный + оверрайды), локальные ключи перезаписывают секционные
                raw_cfg: dict | None = None
                if sec_raw_cfg or override_cfg:
                    raw_cfg = dict(sec_raw_cfg or {})
                    raw_cfg.update(dict(override_cfg or {}))
                cfg_key = _freeze_cfg(raw_cfg or {})
                bkey = (adapter_cls.name, cfg_key)
                adapter = bound_cache.get(bkey)
                if adapter is None:
                    adapter = adapter_cls.bind(raw_cfg)
                    bound_cache[bkey] = adapter

                raw_text = read_text(fp)
                ext = fp.suffix.lstrip(".") if fp.is_file() else ""

                # Эвристики пропуска на уровне адаптера (пустые уже отфильтрованы в Manifest)
                if adapter.name != "base" and adapter.should_skip(fp, raw_text, ext):
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
                    processed_text, meta = adapter.process(raw_text, ext, group_size, bool(grp.mixed))
                    # добавим диагностическую «крошку» про использованные ключи конфигурации
                    if raw_cfg:
                        keys = sorted(raw_cfg.keys())
                        # не зашумляем, если ключей 1-2 — но это всё равно полезно при отладке
                        meta = dict(meta or {})
                        meta["_adapter_cfg_keys"] = ",".join(keys)

                    # Всегда добавляем прозрачные метки группы — для тестов и диагностики
                    meta = dict(meta or {})
                    meta["_group_size"] = group_size
                    meta["_group_mixed"] = grp.mixed
                    meta["_group_lang"] = grp.lang
                    meta["_section"] = e.section_id.as_key()

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
