from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Tuple, Iterable, Optional

import tiktoken

from .config.model import Config
from .context import generate_context, collect_sections_with_counts
from .core.cache import Cache
from .core.generator import generate_listing
from .core.plan import collect_processed_blobs

# --------------------------------------------------------------------------- #
# предустановленные модели и их окна
# --------------------------------------------------------------------------- #

MODEL_CTX = {
    "o3": 32_000,
    "gpt-4o": 128_000,
    "gpt-4o-mini": 25_000,
    "claude-3-opus": 200_000,
    "claude-3-sonnet": 200_000,
    "gemini-1.5-pro": 1_000_000,
}
DEFAULT_MODEL = "o3"

# --------------------------------------------------------------------------- #
# dataclass для статистики
# --------------------------------------------------------------------------- #

@dataclass
class FileStat:
    path: str
    size: int       # bytes
    tokens: int

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _ensure_model(model_name: str) -> Tuple[str, int, "tiktoken.Encoding", str]:
    """
    Возвращает (name, ctx_limit, encoder, encoder_name).
    Для 'o3' используем энкодер gpt-4o. Для неизвестных моделей — cl100k_base.
    """
    if model_name not in MODEL_CTX:
        raise RuntimeError(
            f"Unknown model '{model_name}'. "
            f"Known models: {', '.join(MODEL_CTX)}"
        )
    ctx_limit = MODEL_CTX[model_name]
    encoder_name = "gpt-4o" if model_name == "o3" else model_name
    try:
        enc = tiktoken.encoding_for_model(encoder_name)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")
        encoder_name = "cl100k_base"
    return model_name, ctx_limit, enc, encoder_name

def _count_tokens_for_file(fp: Path, enc: "tiktoken.Encoding") -> int:
    tokens = 0
    with fp.open("rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            tokens += len(enc.encode(chunk.decode("utf-8", errors="ignore")))
    return tokens

def _build_file_stats(
    collected: List[Tuple[Path, str, int]],
    enc: "tiktoken.Encoding",
) -> List[FileStat]:
    stats: List[FileStat] = []
    for fp, rel_posix, size_bytes in collected:
        tokens = _count_tokens_for_file(fp, enc)
        stats.append(FileStat(rel_posix, size_bytes, tokens))
    return stats

def _dedup_files(collected_lists: List[List[Tuple[Path, str, int]]]) -> List[Tuple[Path, str, int]]:
    """
    Принять несколько списков (fp, rel_posix, size) и вернуть объединение без дубликатов
    по абсолютному пути файла.
    """
    seen: Set[Path] = set()
    out: List[Tuple[Path, str, int]] = []
    for lst in collected_lists:
        for fp, rel, size in lst:
            if fp in seen:
                continue
            seen.add(fp)
            out.append((fp, rel, size))
    return out


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #

def collect_stats(
    *,
    scope: str,  # "section" | "context"
    root: Path,
    cfgs: List[Config],
    mode: str,
    model_name: str,
    stats_mode: str,
    cache: Cache,
    context_sections: Optional[Iterable[str]],
    context_name: Optional[str] = None,
    context_section_counts: Optional[Dict[str, int]] = None,
    configs_map: Optional[Dict[str, Config]] = None,
) -> dict:
    # собираем entries/blobs, затем считаем
    name, ctx_limit, enc, encoder_name = _ensure_model(model_name)

    # собираем post-adapter blobs секционно и объединяем
    blobs_all: List[Tuple[str, int, str, Dict, str]] = []
    raw_lists: List[List[Tuple[Path, str, int]]] = []

    # Помощник для умножения на кратность секций (context scope)
    section_counts: Dict[str, int] = {}
    if scope == "context":
        # если передали counts, используем их; иначе вычислим (на всякий)
        if context_section_counts:
            section_counts = dict(context_section_counts)
        elif context_name and configs_map:
            section_counts = collect_sections_with_counts(context_name, root=root, configs=configs_map)
        else:
            section_counts = {}

    # Сбор файлов/блобов помодульно
    if stats_mode == "raw":
        # Для raw нам нужны списки файлов (fp, rel, size)
        for cfg in cfgs:
            raw = generate_listing(root=root, cfg=cfg, mode=mode, list_only=True, _return_stats=True)
            raw_lists.append(raw)
    else:
        # processed/rendered опираются на post-adapter тексты
        for cfg in cfgs:
            blobs = collect_processed_blobs(root=root, cfg=cfg, mode=mode, cache=cache)
            blobs_all.extend(blobs)

    files_rows: List[dict] = []
    meta_summary: Dict[str, int] = {}
    total_raw_tokens = 0
    total_proc_tokens = 0
    total_size = 0

    if stats_mode == "raw":
        files = _dedup_files(raw_lists)
        stats_raw = _build_file_stats(files, enc)
        for s in stats_raw:
            total_size += s.size
            mult = 1
            # В CONTEXT raw считаем с кратностью секций (приближённо: на уровне файлов секций суммируем кратности всех секций, в которые файл попал).
            # Здесь у нас нет отображения file→section, поэтому считаем по файлам уникально (как в SECTION).
            # Точный учёт кратности реализуется ниже в processed/rendered, где есть rel-пути.
            if scope == "context":
                mult = 1  # см. комментарий: raw остаётся «как есть», экономия/оверехед показываем через processed/rendered
            total_raw_tokens += s.tokens * mult
            files_rows.append({
                "path": s.path,
                "sizeBytes": s.size,
                "tokensRaw": s.tokens,
                "tokensProcessed": s.tokens,
                "savedTokens": 0,
                "savedPct": 0.0,
                "promptShare": 0.0,  # заполним после вычисления total_proc_tokens
                "ctxShare": 0.0,
                "meta": {},
            })
        total_proc_tokens = total_raw_tokens
    else:
        # дедуп по абсолютному пути; оставляем первый встретившийся запись
        deduped: Dict[Path, Tuple[str, int, str, Dict, str]] = {}
        for rel, size_raw, text_proc, meta, text_raw in blobs_all:
            # тут нет абсолютного пути; восстановим его через rel из entries заново — надёжнее: используем rel как ключ
            # (абсолютные пути между секциями одинаковые в пределах одного root)
            # создаём ключ по rel, так как collect_processed_blobs уже работает от общего root
            key = Path(rel)
            if key in deduped:
                continue
            deduped[key] = (rel, size_raw, text_proc, meta, text_raw)

        # Определяем множители кратности для CONTEXT (по относительному пути файла).
        # Для SECTION все множители = 1.
        # При scope=context нет прямого соответствия "файл→секция". Для честной кратности
        # суммируем вклад файла умноженный на Σ(counts по секциям, где этот rel встретился).
        # Для этого прогоняем сбор blobs по секциям отдельно: но у нас уже смешанный dedup.
        # Упрощение: считаем множитель = Σ(counts) по всем секциям (т.к. rel уникален по root).
        # Это корректно, если один и тот же файл включён несколькими секциями (типичный случай).
        default_mult = 1
        mult_by_rel: Dict[str, int] = {}
        if scope == "context" and context_section_counts and configs_map:
            # Построим обратный индекс rel→сумма кратностей секций, которые этот rel содержат.
            for sec_name, cnt in context_section_counts.items():
                sec_cfg = configs_map.get(sec_name)
                if not sec_cfg:
                    continue
                sec_blobs = collect_processed_blobs(root=root, cfg=sec_cfg, mode=mode, cache=cache)
                for (rel_s, _sz, _tp, _m, _tr) in sec_blobs:
                    mult_by_rel[rel_s] = mult_by_rel.get(rel_s, 0) + int(cnt)

        for (rel, size_raw, text_proc, meta, text_raw) in deduped.values():
            t_proc_one = len(enc.encode(text_proc))
            t_raw_one = len(enc.encode(text_raw or ""))
            mult = default_mult
            if scope == "context" and mult_by_rel:
                mult = max(1, mult_by_rel.get(rel, 1))
            total_proc_tokens += t_proc_one * mult
            total_raw_tokens += t_raw_one * mult
            total_size += size_raw * 1  # sizeBytes считаем без кратности (физический размер)
            files_rows.append({
                "path": rel,
                "sizeBytes": size_raw,
                "tokensRaw": t_raw_one * mult,
                "tokensProcessed": t_proc_one * mult,
                "savedTokens": max(0, (t_raw_one - t_proc_one) * mult),
                "savedPct": (1 - t_proc_one / t_raw_one) * 100 if t_raw_one else 0.0,
                "promptShare": 0.0,  # заполним ниже
                "ctxShare": 0.0,
                "meta": meta or {},
            })
            for k, v in (meta or {}).items():
                try:
                    vv = int(v) if isinstance(v, bool) else v
                    if isinstance(vv, (int, float)):
                        meta_summary[k] = meta_summary.get(k, 0) + vv
                except Exception:
                    pass

    # теперь можем заполнить shares
    for row in files_rows:
        tp = row["tokensProcessed"]
        row["promptShare"] = (tp / total_proc_tokens * 100) if total_proc_tokens else 0.0
        row["ctxShare"] = (tp / ctx_limit * 100) if ctx_limit else 0.0

    result = {
        "formatVersion": 3,
        "scope": scope,
        "statsMode": stats_mode,
        "model": name,
        "encoder": encoder_name,
        "ctxLimit": ctx_limit,
        "total": {
            "sizeBytes": total_size,
            "tokensProcessed": total_proc_tokens,
            "tokensRaw": total_raw_tokens,
            "savedTokens": max(0, total_raw_tokens - total_proc_tokens),
            "savedPct": (1 - total_proc_tokens / total_raw_tokens) * 100 if total_raw_tokens else 0.0,
            "ctxShare": (total_proc_tokens / ctx_limit * 100) if ctx_limit else 0.0,
            "metaSummary": meta_summary if stats_mode != "raw" else {},
        },
        "files": files_rows,
    }

    if scope == "context":
        sections_used = {}
        if context_section_counts:
            sections_used = dict(context_section_counts)
        elif context_sections is not None:
            # совместимость: если не дали counts — соберём единичные
            sections_used = {name: 1 for name in context_sections}
        ctx_block = {
            "templateName": context_name or "",
            "sectionsUsed": sections_used,
        }
        result["context"] = ctx_block

    if stats_mode == "rendered":
        import sys
        from io import StringIO
        if scope == "section":
            # рендер секционных листингов подряд (как раньше)
            buf, old = StringIO(), sys.stdout
            sys.stdout = buf
            try:
                from .core.generator import generate_listing as _gen
                for _cfg in cfgs:
                    _gen(root=root, cfg=_cfg, mode=mode, list_only=False)
            finally:
                sys.stdout = old
            rendered_tokens = len(enc.encode(buf.getvalue()))
            result["total"]["renderedTokens"] = rendered_tokens
            result["total"]["renderedOverheadTokens"] = max(0, rendered_tokens - total_proc_tokens)
        else:
            # scope=context — рендерим ВЕСЬ шаблон
            if not (context_name and configs_map):
                raise RuntimeError("context stats require context_name and configs_map")
            # 1) Полный рендер шаблона
            buf_full, old = StringIO(), sys.stdout
            sys.stdout = buf_full
            try:
                generate_context(
                    context_name=context_name,
                    configs=configs_map,
                    list_only=False,
                    cache=cache,
                )
            finally:
                sys.stdout = old
            final_rendered_tokens = len(enc.encode(buf_full.getvalue()))
            # 2) Сумма рендера секций * кратность (без шаблонного «клея»)
            from .core.generator import generate_listing as _gen
            sum_sections_rendered = 0
            for sec_name, cnt in (context_section_counts or {}).items():
                cfg = configs_map[sec_name]
                buf_sec = StringIO()
                sys.stdout, old2 = buf_sec, sys.stdout
                try:
                    _gen(root=root, cfg=cfg, mode=mode, list_only=False)
                finally:
                    sys.stdout = old2
                sum_sections_rendered += len(enc.encode(buf_sec.getvalue())) * int(cnt)
            template_only = max(0, final_rendered_tokens - sum_sections_rendered)
            result["total"]["renderedTokens"] = total_proc_tokens + max(0, result["total"]["renderedOverheadTokens"] if "renderedOverheadTokens" in result["total"] else 0)
            # В контексте «renderedTokens» как суммарный итог — это просто final_rendered_tokens
            result["total"]["renderedTokens"] = final_rendered_tokens
            result["total"]["renderedOverheadTokens"] = max(0, final_rendered_tokens - total_proc_tokens)
            # Заполняем блок context
            if "context" not in result:
                result["context"] = {"templateName": context_name or "", "sectionsUsed": {}}
            result["context"]["finalRenderedTokens"] = final_rendered_tokens
            result["context"]["templateOnlyTokens"] = template_only
            result["context"]["templateOverheadPct"] = (template_only / final_rendered_tokens * 100.0) if final_rendered_tokens else 0.0

    return result