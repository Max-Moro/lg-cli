from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Set, Tuple, Iterable, Optional

import tiktoken

from .config.model import Config
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

def _ensure_model(model_name: str) -> Tuple[str, int, "tiktoken.Encoding"]:
    """
    Проверяем известность модели, возвращаем (name, ctx_limit, encoder).
    Для совместимости считаем токены 'o3' энкодером gpt-4o.
    """
    if model_name not in MODEL_CTX:
        raise RuntimeError(
            f"Unknown model '{model_name}'. "
            f"Known models: {', '.join(MODEL_CTX)}"
        )
    ctx_limit = MODEL_CTX[model_name]
    enc = tiktoken.encoding_for_model(model_name if model_name != "o3" else "gpt-4o")
    return model_name, ctx_limit, enc

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
) -> dict:
    # собираем entries из всех секций и дедупим по абсолютному пути
    # затем считаем по processed-блобам (с кэшем)
    name, ctx_limit, enc = _ensure_model(model_name)

    # собираем post-adapter blobs секционно и объединяем
    blobs_all: List[Tuple[str, int, str, Dict, str]] = []
    raw_lists: List[List[Tuple[Path, str, int]]] = []

    for cfg in cfgs:
        if stats_mode == "raw":
            raw = generate_listing(root=root, cfg=cfg, mode=mode, list_only=True, _return_stats=True)
            raw_lists.append(raw)
        else:
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
            total_raw_tokens += s.tokens
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
        for (rel, size_raw, text_proc, meta, text_raw) in deduped.values():
            t_proc = len(enc.encode(text_proc))
            t_raw = len(enc.encode(text_raw or ""))
            total_proc_tokens += t_proc
            total_raw_tokens += t_raw
            total_size += size_raw
            files_rows.append({
                "path": rel,
                "sizeBytes": size_raw,
                "tokensRaw": t_raw,
                "tokensProcessed": t_proc,
                "savedTokens": max(0, t_raw - t_proc),
                "savedPct": (1 - t_proc / t_raw) * 100 if t_raw else 0.0,
                "promptShare": 0.0,  # заполним ниже
                "ctxShare": 0.0,
                "meta": meta or {},
            })
            for k, v in (meta or {}).items():
                try:
                    meta_summary[k] = meta_summary.get(k, 0) + (int(v) if isinstance(v, bool) else v)
                except Exception:
                    pass

    # теперь можем заполнить shares
    for row in files_rows:
        tp = row["tokensProcessed"]
        row["promptShare"] = (tp / total_proc_tokens * 100) if total_proc_tokens else 0.0
        row["ctxShare"] = (tp / ctx_limit * 100) if ctx_limit else 0.0

    result = {
        "formatVersion": 2,
        "scope": scope,
        "statsMode": stats_mode,
        "model": name,
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

    if scope == "context" and context_sections is not None:
        result["context"] = {"sectionsUsed": list(context_sections)}

    if stats_mode == "rendered":
        # рендерим суммарный листинг для одной секции или для каждой секции подряд (без шаблона),
        # т.к. renderedTokens — это «что реально выведем через generate_listing» для данных cfg(s).
        import sys
        from io import StringIO
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

    return result