import os
from pathlib import Path

from lg.stats import collect_stats
from lg.config import Config
from lg.filters.model import FilterNode
from lg.adapters.markdown import LangMarkdown


def _write(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_stats_processed_reduces_markdown_tokens(tmp_path: Path):
    """
    Для Markdown адаптер удаляет одиночный H1 при group_size=1 и max_heading_level задан.
    В processed-режиме это должно отражаться как уменьшение токенов относительно raw.
    """
    # Один markdown-файл с H1 + короткий текст
    _write(tmp_path, "README.md", "# Title\nBody line\n")

    cfg = Config(
        extensions=[".md"],
        filters=FilterNode(mode="block"),  # default-allow
        markdown=LangMarkdown(max_heading_level=2),
        code_fence=True,   # не важно: md-only → fence не применится
    )

    raw = collect_stats(root=tmp_path, cfg=cfg, mode="all", model_name="o3", stats_mode="raw")
    processed = collect_stats(root=tmp_path, cfg=cfg, mode="all", model_name="o3", stats_mode="processed")

    assert raw["total"]["tokens"] > 0
    assert processed["total"]["tokens"] > 0
    # processed должен быть строже (H1 удалён)
    assert processed["total"]["tokens"] < raw["total"]["tokens"]


def test_stats_rendered_adds_overhead_with_fence(tmp_path: Path):
    """
    В rendered-режиме считаем весь отрендеренный листинг.
    Для не-Markdown файлов при включённом fence должны появляться дополнительные токены
    (обёртки ```lang и маркеры файлов).
    """
    _write(tmp_path, "a.py", "print('a')\n")
    _write(tmp_path, "b.py", "print('b')\n")

    cfg = Config(
        extensions=[".py"],
        filters=FilterNode(mode="block"),
        code_fence=True,
    )

    processed = collect_stats(root=tmp_path, cfg=cfg, mode="all", model_name="o3", stats_mode="processed")
    rendered = collect_stats(root=tmp_path, cfg=cfg, mode="all", model_name="o3", stats_mode="rendered")

    # rendered содержит дополнительные символы/токены
    assert "renderedTokens" in rendered["total"]
    assert "renderedOverheadTokens" in rendered["total"]
    assert rendered["total"]["renderedTokens"] >= processed["total"]["tokens"]
    assert rendered["total"]["renderedOverheadTokens"] > 0
