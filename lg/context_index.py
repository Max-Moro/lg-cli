"""
Сервис построения карты кратностей для файлов в «контекстном» шаблоне.

Назначение: для scope=context в stats.collect_stats быстро получить
  rel_path → Σ(counts по секциям, где этот файл встречается).
"""
from typing import Dict, Mapping
from pathlib import Path

from .config.model import Config
from .core.cache import Cache
from .core.plan import collect_processed_blobs


def compute_context_rel_multiplicity(
    *,
    root: Path,
    configs_map: Mapping[str, Config],
    context_section_counts: Mapping[str, int],
    mode: str,
    cache: Cache,
) -> Dict[str, int]:
    """
    Построить словарь rel_path → суммарная кратность появления файла во всех секциях,
    используемых контекстом (учитывает веса секций).
    """
    mult_by_rel: Dict[str, int] = {}
    for sec_name, cnt in context_section_counts.items():
        cfg = configs_map.get(sec_name)
        if not cfg:
            continue
        blobs = collect_processed_blobs(root=root, cfg=cfg, mode=mode, cache=cache)
        for b in blobs:
            mult_by_rel[b.rel_path] = mult_by_rel.get(b.rel_path, 0) + int(cnt)
    return mult_by_rel
