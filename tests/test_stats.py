from __future__ import annotations

from pathlib import Path
import textwrap
import pytest

from lg.engine import run_report
from lg.types import RunOptions


# --------------------------- helpers --------------------------- #

def _w(p: Path, txt: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    return p


def _mkproj_md_only(root: Path, *, code_fence: bool = True, max_h: int | None = 2) -> None:
    """Минимальный проект: секция all → только .md (для md-only режимов рендера)."""
    _w(
        root / "lg-cfg" / "sections.yaml",
        textwrap.dedent(f"""
        schema_version: 6
        all:
          extensions: [".md"]
          code_fence: {str(code_fence).lower()}
          markdown:
            max_heading_level: {max_h if max_h is not None else 'null'}
        """).strip() + "\n",
    )


def _mkproj_py_only(root: Path, *, code_fence: bool = True) -> None:
    """Минимальный проект: секция all → только .py (для кодовых режимов рендера)."""
    _w(
        root / "lg-cfg" / "sections.yaml",
        textwrap.dedent(f"""
        schema_version: 6
        all:
          extensions: [".py"]
          code_fence: {str(code_fence).lower()}
        """).strip() + "\n",
    )


# ============================ TESTS ============================ #

def test_md_with_h1_processed_saves_tokens_and_meta(tmp_path: Path, monkeypatch):
    """
    Для Markdown адаптер удаляет одиночный H1 при group_size=1
    и заданном max_heading_level → processed < raw.
    """
    _mkproj_md_only(tmp_path, code_fence=True, max_h=2)
    _w(tmp_path / "README.md", "# Title\nBody line\n")
    monkeypatch.chdir(tmp_path)

    report = run_report("sec:all", RunOptions())
    total = report.total

    assert total.tokensProcessed > 0
    assert total.tokensRaw > total.tokensProcessed   # «экономия» токенов после адаптера
    assert total.savedTokens == total.tokensRaw - total.tokensProcessed
    assert total.savedPct > 0.0
    # Адаптер пишет метрику removed_h1 → аккумулируется в metaSummary
    assert report.total.metaSummary.get("md.removed_h1", 0) >= 1


def test_md_without_h1_no_overhead(tmp_path: Path, monkeypatch):
    """
    Markdown без H1: адаптер ничего не удаляет → processed == raw.
    md-only рендер (без code fence и маркеров) → renderedOverheadTokens == 0.
    """
    _mkproj_md_only(tmp_path, code_fence=True, max_h=2)
    _w(tmp_path / "README.md", "Body line\n")  # без H1
    monkeypatch.chdir(tmp_path)

    report = run_report("sec:all", RunOptions())
    total = report.total

    assert total.tokensProcessed > 0
    assert total.tokensProcessed == total.tokensRaw
    assert total.renderedTokens == total.tokensProcessed
    assert total.renderedOverheadTokens == 0

    # финальный документ совпадает с пайплайном, шаблонов нет
    assert report.context is None


def test_non_md_with_fence_adds_overhead(tmp_path: Path, monkeypatch):
    """
    Порт старого теста «rendered добавляет оверхед с fence» для кода:
    при code_fence=True для .py появляются ```lang и маркеры файлов → есть оверхед.
    """
    _mkproj_py_only(tmp_path, code_fence=True)
    _w(tmp_path / "a.py", "print('a')\n")
    _w(tmp_path / "b.py", "print('b')\n")
    monkeypatch.chdir(tmp_path)

    report = run_report("sec:all", RunOptions(code_fence=True))
    total = report.total

    assert total.tokensProcessed > 0
    assert "renderedTokens" in total.model_dump()
    assert "renderedOverheadTokens" in total.model_dump()
    assert total.renderedTokens >= total.tokensProcessed
    assert total.renderedOverheadTokens > 0


def test_non_md_no_fence_but_markers_overhead(tmp_path: Path, monkeypatch):
    """
    Даже при code_fence=False для «кодового»/смешанного содержимого
    мы печатаем маркеры '# —— FILE: … ——', поэтому оверхед всё равно > 0.
    """
    _mkproj_py_only(tmp_path, code_fence=False)
    _w(tmp_path / "a.py", "print('a')\n")
    _w(tmp_path / "b.py", "print('b')\n")
    monkeypatch.chdir(tmp_path)

    report = run_report("sec:all", RunOptions(code_fence=False))
    total = report.total

    assert total.tokensProcessed > 0
    assert total.renderedTokens >= total.tokensProcessed
    assert total.renderedOverheadTokens > 0


def test_context_template_overhead_and_ctx_block(tmp_path: Path, monkeypatch):
    """
    Контекст с «клеем» (Intro/Outro): проверяем templateOnlyTokens > 0,
    заполненность финальных полей контекста и согласованность finalCtxShare.
    """
    _mkproj_py_only(tmp_path, code_fence=True)
    _w(tmp_path / "m.py", "x = 1\n")
    _w(tmp_path / "lg-cfg" / "glued.ctx.md", "Intro\n\n${all}\n\nOutro\n")

    monkeypatch.chdir(tmp_path)
    report = run_report("ctx:glued", RunOptions())

    ctx = report.context
    assert ctx.templateName == "ctx:glued"
    assert ctx.sectionsUsed == {".::all": 1}
    assert isinstance(ctx.finalRenderedTokens, int) and ctx.finalRenderedTokens > 0
    assert isinstance(ctx.templateOnlyTokens, int) and ctx.templateOnlyTokens > 0
    # финальный share должен считаться от finalRenderedTokens
    assert pytest.approx(ctx.finalCtxShare, rel=1e-6) == ctx.finalRenderedTokens / report.ctxLimit * 100.0

    # иерархия уровней токенов: processed ≤ rendered ≤ final
    assert report.total.tokensProcessed <= report.total.renderedTokens <= ctx.finalRenderedTokens


def test_prompt_shares_sum_to_100(tmp_path: Path, monkeypatch):
    """
    Проверяем стабильность распределения вкладов: сумма promptShare ≈ 100%.
    """
    _mkproj_py_only(tmp_path, code_fence=True)
    _w(tmp_path / "a.py", "print('a')\n")
    _w(tmp_path / "b.py", "print('b')\n")
    monkeypatch.chdir(tmp_path)

    report = run_report("sec:all", RunOptions())
    shares = sum(f.promptShare for f in report.files)

    assert 99.9 <= shares <= 100.1
