from pathlib import Path

from lg.adapters.markdown import LangMarkdown
from lg.config import Config
from lg.core.cache import Cache
from lg.filters.model import FilterNode
from lg.stats import collect_stats


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

    cache = Cache(tmp_path)
    raw = collect_stats(scope="section", root=tmp_path, cfgs=[cfg], mode="all", model_name="o3", stats_mode="raw", cache=cache, context_sections=None)
    processed = collect_stats(scope="section", root=tmp_path, cfgs=[cfg], mode="all", model_name="o3", stats_mode="processed", cache=cache, context_sections=None)

    assert raw["total"]["tokensProcessed"] > 0
    assert processed["total"]["tokensProcessed"] > 0
    # processed должен быть строже (H1 удалён)
    assert processed["total"]["tokensProcessed"] < raw["total"]["tokensProcessed"]


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

    cache = Cache(tmp_path)
    processed = collect_stats(scope="section", root=tmp_path, cfgs=[cfg], mode="all", model_name="o3", stats_mode="processed", cache=cache, context_sections=None)
    rendered = collect_stats(scope="section", root=tmp_path, cfgs=[cfg], mode="all", model_name="o3", stats_mode="rendered", cache=cache, context_sections=None)

    # rendered содержит дополнительные символы/токены
    assert "renderedTokens" in rendered["total"]
    assert "renderedOverheadTokens" in rendered["total"]
    assert rendered["total"]["renderedTokens"] >= processed["total"]["tokensProcessed"]
    assert rendered["total"]["renderedOverheadTokens"] > 0
