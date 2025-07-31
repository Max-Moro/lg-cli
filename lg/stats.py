from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Callable

import tiktoken

from .core.generator import generate_listing
from .config.model import Config

# --------------------------------------------------------------------------- #
# 1. предустановленные модели и их окна
# --------------------------------------------------------------------------- #

MODEL_CTX = {
    "o3": 200_000,
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
# 3. helper — человекочитаемый размер
# --------------------------------------------------------------------------- #


def _hr_size(n: int) -> str:
    for unit in ["bytes", "KiB", "MiB", "GiB"]:
        if n < 1024 or unit == "GiB":
            return f"{n:.1f} {unit}" if unit != "bytes" else f"{n} {unit}"
        n /= 1024
    return f"{n:.1f} GiB"

# --------------------------------------------------------------------------- #
# 4. public API
# --------------------------------------------------------------------------- #


def collect_stats_and_print(
    *,
    root: Path,
    cfg: Config,
    mode: str,
    sort_key: str,
    model_name: str,
):
    # 4.1. проверяем модель
    if model_name not in MODEL_CTX:
        raise RuntimeError(
            f"Unknown model '{model_name}'. "
            f"Known models: {', '.join(MODEL_CTX)}"
        )
    ctx_limit = MODEL_CTX[model_name]
    enc = tiktoken.encoding_for_model(model_name if model_name != "o3" else "gpt-4o")

    # 4.2. собираем FileStat при помощи generate_listing(list_only)
    collected = generate_listing(
        root=root,
        cfg=cfg,
        mode=mode,
        list_only=True,
        _return_stats=True,      # внутренний флаг
    )
    stats: List[FileStat] = []
    for fp, rel_posix, size_bytes in collected:
        # токены считаем построчно без загрузки всего файла (memory-safe)
        tokens = 0
        with fp.open("rb") as fh:
            for chunk in iter(lambda: fh.read(8192), b""):
                tokens += len(enc.encode(chunk.decode("utf-8", errors="ignore")))
        stats.append(FileStat(rel_posix, size_bytes, tokens))

    if not stats:
        print("(no files)")
        return

    total_tokens = sum(s.tokens for s in stats)

    # 4.3. сортировка
    KEY: dict[str, Callable[[FileStat], object]] = {
        "path":  lambda s: s.path,
        "size":  lambda s: (-s.size, s.path),
        "share": lambda s: (-s.tokens, s.path),
    }
    stats.sort(key=KEY[sort_key])

    # 4.4. печать ASCII-таблицы
    print(
        "PATH".ljust(40),
        "SIZE".rjust(9),
        "TOKENS".rjust(9),
        "PROMPT%".rjust(8),
        "CTX%".rjust(6),
    )
    print("─" * 40, "─" * 9, "─" * 9, "─" * 8, "─" * 6, sep="")

    for s in stats:
        share_prompt = s.tokens / total_tokens * 100
        share_ctx = s.tokens / ctx_limit * 100
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
        f"{total_tokens}".rjust(9),
        "100 %".rjust(8),
        f"{total_tokens / ctx_limit * 100:5.1f}%".rjust(6),
    )
