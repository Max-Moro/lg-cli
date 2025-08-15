from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import tiktoken

from ..cache.fs_cache import Cache
from ..manifest.builder import Manifest
from ..types import ContextSpec
from ..types import (
    FileRow, Totals, ContextBlock, ProcessedBlob, RenderedDocument,
)

# —————————— модель → (ctx_limit, encoder_name, encoder) —————————— #
_MODEL_CTX = {
    "o3": 32_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 25_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "gemini-1.5-pro": 1_000_000,
}


@dataclass(frozen=True)
class _EncInfo:
    model: str
    ctx_limit: int
    enc_name: str
    enc: "tiktoken.Encoding"


def _enc_for_model(model: str) -> _EncInfo:
    if model not in _MODEL_CTX:
        # Неизвестную модель считаем «о3» семантически, но с cl100k_base
        ctx = 32_000
        try:
            enc = tiktoken.get_encoding("cl100k_base")
        except Exception:
            enc = tiktoken.get_encoding("cl100k_base")
        return _EncInfo(model=model, ctx_limit=ctx, enc_name="cl100k_base", enc=enc)

    ctx = _MODEL_CTX[model]
    enc_name = "gpt-4o" if model == "o3" else model
    try:
        enc = tiktoken.encoding_for_model(enc_name)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
        enc_name = "cl100k_base"
    return _EncInfo(model=model, ctx_limit=ctx, enc_name=enc_name, enc=enc)


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
    rendered: RenderedDocument,
    spec: ContextSpec,
    manifest: Manifest,
    model_name: str,
    cache: Cache,
) -> Tuple[List[FileRow], Totals, ContextBlock, str, int]:
    """
    Считает:
      • tokensRaw / tokensProcessed на файлах (с учётом кратности из Manifest)
      • renderedTokens на всём документе
      • shares и агрегаты
    Возвращает (files_rows, totals, context_block, encoder_name, ctx_limit)
    """
    enc_info = _enc_for_model(model_name)
    enc = enc_info.enc

    # кратности по rel_path из Manifest
    mult_by_rel: Dict[str, int] = {fr.rel_path: fr.multiplicity for fr in manifest.files}

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
        t_proc_cached = cache.get_tokens(p_path, model=enc_info.model, mode="processed")
        t_proc = t_proc_cached if isinstance(t_proc_cached, int) else len(enc.encode(b.processed_text))
        if not isinstance(t_proc_cached, int):
            cache.update_tokens(p_path, model=enc_info.model, mode="processed", value=t_proc)

        # tokensRaw
        r_path = cache.path_for_raw_tokens_key(b.cache_key_raw)
        t_raw_cached = cache.get_tokens(r_path, model=enc_info.model, mode="raw")
        t_raw = t_raw_cached if isinstance(t_raw_cached, int) else len(enc.encode(b.raw_text))
        if not isinstance(t_raw_cached, int):
            cache.update_tokens(r_path, model=enc_info.model, mode="raw", value=t_raw)

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
            ctxShare=(t_proc * mult / enc_info.ctx_limit * 100.0) if enc_info.ctx_limit else 0.0,
            meta=b.meta or {},
        )
        for _, b, t_raw, t_proc, mult, saved_tokens, saved_pct in temp_rows
    ]

    # rendered tokens для ВСЕГО документа (один раз)
    # Ключ rendered кэша зависит от имени контекста, кратностей, опций и processed-ключей.
    processed_keys = {rel: b.cache_key_processed for rel, b in dedup.items()}
    options_fp = {
        "mode": "all",  # статистика от рендера не зависит от VCS-режима; документ уже собран
        "code_fence": True,  # флаг уже «вплавлен» в rendered.text, храним для инвалидации
        "model": enc_info.model,
    }
    # Пытаемся «угадать» code_fence из фактического текста (признак наличия ```):
    if "```" not in (rendered.text or ""):
        options_fp["code_fence"] = False

    k_rendered, p_rendered = cache.build_rendered_key(
        context_name=spec.name if spec.kind == "context" else f"__sec__:{spec.name}",
        sections_used=spec.sections.by_name,
        options_fp=options_fp,
        processed_keys=processed_keys,
    )
    t_rendered_cached = cache.get_rendered_tokens(p_rendered, model=enc_info.model)
    if isinstance(t_rendered_cached, int):
        t_rendered = t_rendered_cached
    else:
        t_rendered = len(enc.encode(rendered.text))
        cache.update_rendered_tokens(p_rendered, model=enc_info.model, value=t_rendered)

    totals = Totals(
        sizeBytes=total_size,
        tokensProcessed=total_proc,
        tokensRaw=total_raw,
        savedTokens=max(0, total_raw - total_proc),
        savedPct=(1 - (total_proc / total_raw)) * 100.0 if total_raw else 0.0,
        ctxShare=(total_proc / enc_info.ctx_limit * 100.0) if enc_info.ctx_limit else 0.0,
        renderedTokens=t_rendered,
        renderedOverheadTokens=max(0, t_rendered - total_proc),
        metaSummary=meta_summary,
    )

    ctx_block = ContextBlock(
        templateName=(spec.kind == "context" and f"ctx:{spec.name}") or f"sec:{spec.name}",
        sectionsUsed=spec.sections.by_name,
        finalRenderedTokens=t_rendered,
        templateOnlyTokens=None,       # можно заполнить позже точной метрикой
        templateOverheadPct=None,
        finalCtxShare=(t_rendered / enc_info.ctx_limit * 100.0) if enc_info.ctx_limit else 0.0,
    )

    return files_rows, totals, ctx_block, enc_info.enc_name, enc_info.ctx_limit
