from __future__ import annotations

from typing import Dict, List, Tuple

import tiktoken

from .model import ResolvedModel
from ..cache.fs_cache import Cache
from ..types import ContextSpec, FileRow, Totals, ContextBlock, ProcessedBlob, Manifest


# —————————— helpers —————————— #

def _sum_numeric_meta(meta: Dict) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for k, v in (meta or {}).items():
        try:
            if isinstance(v, bool):
                v = int(v)
            if isinstance(v, (int, float)):
                out[k] = out.get(k, 0) + int(v)
        except Exception:
            pass
    return out


# —————————— основная функция подсчёта —————————— #

def compute_stats(
    *,
    blobs: List[ProcessedBlob],
    rendered_final_text: str,
    rendered_sections_only_text: str,
    templates_hashes: Dict[str, str],
    spec: ContextSpec,
    manifest: Manifest,
    model_info: ResolvedModel,
    code_fence: bool,
    cache: Cache,
) -> Tuple[List[FileRow], Totals, ContextBlock, str]:
    """
    Считает:
      • tokensRaw / tokensProcessed на файлах (с учётом кратности из Manifest)
      • renderedTokens на финальном документе (с клеем)
      • templateOnlyTokens как разницу между финальным и «sections-only» документом
      • shares и агрегаты
    Возвращает (files_rows, totals, context_block, encoder_name, ctx_limit)
    """

    enc_name = model_info.encoder
    try:
        enc = tiktoken.get_encoding(enc_name)
    except Exception:
        try:
            enc = tiktoken.encoding_for_model(enc_name)
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
            enc_name = "cl100k_base"

    # кратности по rel_path из Manifest
    mult_by_rel: Dict[str, int] = {f.rel_path: f.multiplicity for f in manifest.iter_files()}

    # ---- адресные секции: детерминированная карта для кэша и отчёта ----
    sections_used_map: Dict[str, int] = {}
    for ref in spec.section_refs:
        key = ref.canon.as_key()
        sections_used_map[key] = sections_used_map.get(key, 0) + ref.multiplicity

    # Быстрый доступ к путям кэша по ключам
    # (в Cache добавили публичные методы path_for_*)
    temp_rows = []
    total_raw = 0
    total_proc = 0
    total_size = 0
    meta_summary: Dict[str, int] = {}

    # уникализируем по rel_path: первый blob выигрывает
    dedup: Dict[str, ProcessedBlob] = {}
    for b in blobs:
        if b.rel_path not in dedup:
            dedup[b.rel_path] = b

    for rel, b in dedup.items():
        mult = max(1, mult_by_rel.get(rel, 1))

        # tokensProcessed
        p_path = cache.path_for_processed_key(b.cache_key_processed)
        t_proc_cached = cache.get_tokens(p_path, model=model_info.base, mode="processed")
        t_proc = t_proc_cached if isinstance(t_proc_cached, int) else len(enc.encode(b.processed_text))
        if not isinstance(t_proc_cached, int):
            cache.update_tokens(p_path, model=model_info.base, mode="processed", value=t_proc)

        # tokensRaw
        r_path = cache.path_for_raw_tokens_key(b.cache_key_raw)
        t_raw_cached = cache.get_tokens(r_path, model=model_info.base, mode="raw")
        t_raw = t_raw_cached if isinstance(t_raw_cached, int) else len(enc.encode(b.raw_text))
        if not isinstance(t_raw_cached, int):
            cache.update_tokens(r_path, model=model_info.base, mode="raw", value=t_raw)

        total_proc += t_proc * mult
        total_raw += t_raw * mult
        total_size += b.size_bytes

        for k, v in _sum_numeric_meta(b.meta).items():
            meta_summary[k] = meta_summary.get(k, 0) + v

        saved_tokens = max(0, (t_raw - t_proc) * mult)
        saved_pct = (1 - (t_proc / t_raw)) * 100.0 if t_raw else 0.0

        temp_rows.append(
            (rel, b, t_raw, t_proc, mult, saved_tokens, saved_pct)
        )

    # теперь создаём финальный список с заполненными shares
    files_rows = [
        FileRow(
            path=b.rel_path,
            sizeBytes=b.size_bytes,
            tokensRaw=t_raw * mult,
            tokensProcessed=t_proc * mult,
            savedTokens=saved_tokens,
            savedPct=saved_pct,
            promptShare=(t_proc * mult / total_proc * 100.0) if total_proc else 0.0,
            ctxShare=(t_proc * mult / model_info.ctx_limit * 100.0) if model_info.ctx_limit else 0.0,
            meta=b.meta or {},
        )
        for _, b, t_raw, t_proc, mult, saved_tokens, saved_pct in temp_rows
    ]

    # ключи кэша одинаковые, вариант отличается
    processed_keys = {rel: b.cache_key_processed for rel, b in dedup.items()}
    options_fp = {"code_fence": bool(code_fence)}

    # 1) Чистые секции (без FILE-маркеров, без fenced, без шаблонов)
    k_so, p_so = cache.build_rendered_key(
        context_name=spec.name if spec.kind == "context" else f"__sec__:{spec.name}",
        sections_used=sections_used_map,
        options_fp={**options_fp, "variant": "sections-only"},
        processed_keys=processed_keys,
        templates=templates_hashes,
    )
    t_sections_only = cache.get_rendered_tokens(p_so, model=model_info.base)
    if not isinstance(t_sections_only, int):
        t_sections_only = len(enc.encode(rendered_sections_only_text))
        cache.update_rendered_tokens(p_so, model=model_info.base, value=t_sections_only)

    # 2) После пайплайна (FILE-маркеры + fenced, но без шаблонов)
    k_pipeline, p_pipeline = cache.build_rendered_key(
        context_name=spec.name if spec.kind == "context" else f"__sec__:{spec.name}",
        sections_used=sections_used_map,
        options_fp={**options_fp, "variant": "pipeline"},
        processed_keys=processed_keys,
        templates=templates_hashes,
    )
    t_pipeline = cache.get_rendered_tokens(p_pipeline, model=model_info.base)
    if not isinstance(t_pipeline, int):
        t_pipeline = len(enc.encode(rendered_sections_only_text))
        cache.update_rendered_tokens(p_pipeline, model=model_info.base, value=t_pipeline)

    # 3) Финальный документ (после шаблонов)
    k_final, p_final = cache.build_rendered_key(
        context_name=spec.name if spec.kind == "context" else f"__sec__:{spec.name}",
        sections_used=sections_used_map,
        options_fp={**options_fp, "variant": "final"},
        processed_keys=processed_keys,
        templates=templates_hashes,
    )
    t_final = cache.get_rendered_tokens(p_final, model=model_info.base)
    if not isinstance(t_final, int):
        t_final = len(enc.encode(rendered_final_text))
        cache.update_rendered_tokens(p_final, model=model_info.base, value=t_final)

    totals = Totals(
        sizeBytes=total_size,
        tokensProcessed=total_proc,
        tokensRaw=total_raw,
        savedTokens=max(0, total_raw - total_proc),
        savedPct=(1 - (total_proc / total_raw)) * 100.0 if total_raw else 0.0,
        ctxShare=(total_proc / model_info.ctx_limit * 100.0) if model_info.ctx_limit else 0.0,
        renderedTokens=t_pipeline,
        renderedOverheadTokens=max(0, t_pipeline - total_proc),
        metaSummary=meta_summary,
    )

    ctx_block = ContextBlock(
        templateName=(spec.kind == "context" and f"ctx:{spec.name}") or f"sec:{spec.name}",
        sectionsUsed=sections_used_map,
        finalRenderedTokens=t_final,
        templateOnlyTokens=max(0, t_final - t_pipeline),
        templateOverheadPct=((t_final - t_pipeline) / t_final * 100.0) if t_final else 0.0,
        finalCtxShare=(t_final / model_info.ctx_limit * 100.0) if model_info.ctx_limit else 0.0,
    )

    return files_rows, totals, ctx_block, enc_name
