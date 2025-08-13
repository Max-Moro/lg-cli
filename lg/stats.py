from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Callable, Dict, Set, Tuple

import tiktoken

from .config.model import Config
from .core.generator import generate_listing

# --------------------------------------------------------------------------- #
# 1. предустановленные модели и их окна
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
# 2. dataclass для статистики
# --------------------------------------------------------------------------- #


@dataclass
class FileStat:
    path: str
    size: int       # bytes
    tokens: int

# --------------------------------------------------------------------------- #
# 3. helpers (DRY)
# --------------------------------------------------------------------------- #

def _hr_size(n: int) -> str:
    for unit in ["bytes", "KiB", "MiB", "GiB"]:
        if n < 1024 or unit == "GiB":
            return f"{n:.1f} {unit}" if unit != "bytes" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} GiB"

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

def _sort_stats(stats: List[FileStat], sort_key: str) -> None:
    KEY: dict[str, Callable[[FileStat], object]] = {
        "path":  lambda s: s.path,
        "size":  lambda s: (-s.size, s.path),
        "share": lambda s: (-s.tokens, s.path),
    }
    stats.sort(key=KEY.get(sort_key, KEY["path"]))

def _print_ascii_table(stats: List[FileStat], ctx_limit: int) -> None:
    if not stats:
        print("(no files)")
        return
    total_tokens = sum(s.tokens for s in stats)
    print(
        "PATH".ljust(40),
        "SIZE".rjust(9),
        "TOKENS".rjust(9),
        "PROMPT%".rjust(8),
        "CTX%".rjust(6),
    )
    print("─" * 40, "─" * 9, "─" * 9, "─" * 8, "─" * 6, sep="")
    for s in stats:
        share_prompt = s.tokens / total_tokens * 100 if total_tokens else 0.0
        share_ctx = s.tokens / (ctx_limit or 1) * 100
        overflow = "‼" if share_ctx > 100 else ""
        print(
            s.path.ljust(40)[:40],
            _hr_size(s.size).rjust(9),
            f"{s.tokens}".rjust(9),
            f"{share_prompt:6.1f}%".rjust(8),
            f"{share_ctx:5.1f}%{overflow}".rjust(6 + len(overflow)),
        )
    print("─" * 40, "─" * 9, "─" * 9, "─" * 8, "─" * 6, sep="")
    print(
        "TOTAL".ljust(40),
        _hr_size(sum(s.size for s in stats)).rjust(9),
        f"{sum(s.tokens for s in stats)}".rjust(9),
        "100 %".rjust(8),
        f"{(sum(s.tokens for s in stats) / (ctx_limit or 1) * 100):5.1f}%".rjust(6),
    )

# --------------------------------------------------------------------------- #
# 4. public API (JSON-friendly)
# --------------------------------------------------------------------------- #

def collect_stats(
    *,
    root: Path,
    cfg: Config,
    mode: str,
    model_name: str,
    stats_mode: str = "processed",    # "raw" | "processed" | "rendered"
) -> dict:
    # проверяем модель и получаем encoder
    _, ctx_limit, enc = _ensure_model(model_name)

    # собираем FileStat при помощи generate_listing(list_only)
    if stats_mode == "raw":
        collected = generate_listing(
            root=root,
            cfg=cfg,
            mode=mode,
            list_only=True,
            _return_stats=True,
        )
        stats: List[FileStat] = _build_file_stats(collected, enc)
    else:
        # processed/rendered: считаем по тексту ПОСЛЕ адаптеров
        from .core.generator import _build_processed_blobs_for_stats  # новый helper (см. Шаг 1)
        blobs = _build_processed_blobs_for_stats(root=root, cfg=cfg, mode=mode)
        stats = []
        for rel, size_raw, text_proc in blobs:
            tokens = len(enc.encode(text_proc))
            stats.append(FileStat(rel, size_raw, tokens))

    total_tokens = sum(s.tokens for s in stats)
    result = {
        "model": model_name,
        "ctxLimit": ctx_limit,
        "total": {
            "sizeBytes": sum(s.size for s in stats),
            "tokens": total_tokens,
            "ctxShare": (total_tokens / ctx_limit * 100) if ctx_limit else 0.0,
        },
        "files": [
            {
                "path": s.path,
                "sizeBytes": s.size,
                "tokens": s.tokens,
                "promptShare": (s.tokens / total_tokens * 100) if total_tokens else 0.0,
                "ctxShare": (s.tokens / ctx_limit * 100) if ctx_limit else 0.0,
            }
            for s in stats
        ],
    }
    if stats_mode == "rendered":
        # посчитать токены полного рендера и добавить overhead
        import sys
        from io import StringIO
        buf, old = StringIO(), sys.stdout
        sys.stdout = buf
        try:
            from .core.generator import generate_listing as _gen
            _gen(root=root, cfg=cfg, mode=mode, list_only=False)
        finally:
            sys.stdout = old
        rendered_tokens = len(enc.encode(buf.getvalue()))
        result["total"]["renderedTokens"] = rendered_tokens
        result["total"]["renderedOverheadTokens"] = max(0, rendered_tokens - total_tokens)
    return result

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

def collect_context_stats(
    *,
    root: Path,
    configs: Dict[str, Config],
    context_sections: Set[str],
    model_name: str,
) -> dict:
    """Агрегированная статистика по множеству секций (для контекста)."""
    _, ctx_limit, enc = _ensure_model(model_name)

    collected_lists: List[List[Tuple[Path, str, int]]] = []
    for sec in sorted(context_sections):
        cfg = configs[sec]
        lst = generate_listing(
            root=root, cfg=cfg, mode="all", list_only=True, _return_stats=True
        )
        collected_lists.append(lst)

    files = _dedup_files(collected_lists)

    # Подсчет токенов по уникальным файлам
    items: List[FileStat] = _build_file_stats(files, enc)

    total_tokens = sum(s.tokens for s in items)
    result = {
        "model": model_name,
        "ctxLimit": ctx_limit,
        "total": {
            "sizeBytes": sum(s.size for s in items),
            "tokens": total_tokens,
            "ctxShare": (total_tokens / ctx_limit * 100) if ctx_limit else 0.0,
        },
        "files": [
            {
                "path": s.path,
                "sizeBytes": s.size,
                "tokens": s.tokens,
                "promptShare": (s.tokens / total_tokens * 100) if total_tokens else 0.0,
                "ctxShare": (s.tokens / ctx_limit * 100) if ctx_limit else 0.0,
            }
            for s in items
        ],
    }
    return result

# --------------------------------------------------------------------------- #
# 5. human-friendly print
# --------------------------------------------------------------------------- #
def collect_stats_and_print(
    *,
    root: Path,
    cfg: Config,
    mode: str,
    sort_key: str,
    model_name: str,
    stats_mode: str = "processed",
):
    data = collect_stats(root=root, cfg=cfg, mode=mode, model_name=model_name, stats_mode=stats_mode)
    stats: List[FileStat] = [
        FileStat(path=it["path"], size=it["sizeBytes"], tokens=it["tokens"])
        for it in data["files"]
    ]
    _sort_stats(stats, sort_key)
    _print_ascii_table(stats, data["ctxLimit"])

def context_stats_and_print(
    *,
    root: Path,
    configs: Dict[str, Config],
    context_sections: Set[str],
    model_name: str,
    sort_key: str = "path",   # "path" | "size" | "share"
):
    data = collect_context_stats(
        root=root,
        configs=configs,
        context_sections=context_sections,
        model_name=model_name,
    )
    stats: List[FileStat] = [
        FileStat(path=it["path"], size=it["sizeBytes"], tokens=it["tokens"])
        for it in data["files"]
    ]
    _sort_stats(stats, sort_key)
    _print_ascii_table(stats, data["ctxLimit"])