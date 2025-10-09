"""
Тесты расчета статистики по токенам.

Переписаны из tests/test_stats.py с использованием новой
инфраструктуры тестирования.

Проверяют:
- Корректность подсчета токенов для обработанных файлов
- Расчет экономии токенов адаптерами
- Оверхеды от рендеринга (fence, маркеры файлов)
- Статистику на уровне контекста (template overhead)
- Распределение долей (shares) в промте
"""

from pathlib import Path
import pytest

from tests.infrastructure import write, make_run_options, make_engine
from lg.engine import _parse_target


# ==================== Хелперы для создания проектов ====================

def create_md_only_project(root: Path, *, max_h: int | None = 2, strip_h1: bool = False) -> None:
    """Создает минимальный проект с секцией для markdown файлов."""
    write(
        root / "lg-cfg" / "sections.yaml",
        f"""all:
  extensions: [".md"]
  markdown:
    max_heading_level: {max_h if max_h is not None else 'null'}
    strip_h1: {str(strip_h1).lower()}
  filters:
    mode: allow
    allow:
      - "/**"
""",
    )


def create_py_only_project(root: Path) -> None:
    """Создает минимальный проект с секцией для Python файлов."""
    write(
        root / "lg-cfg" / "sections.yaml",
        """all:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/**"
""",
    )


# ==================== Тесты Markdown оптимизаций ====================

class TestMarkdownOptimizations:
    """Тесты оптимизации токенов для Markdown файлов."""
    
    def test_md_with_h1_processed_saves_tokens(self, tmp_path: Path):
        """
        Для Markdown адаптер удаляет одиночный H1 при group_size=1
        и заданном max_heading_level → processed < raw.
        """
        create_md_only_project(tmp_path, max_h=2, strip_h1=True)
        write(tmp_path / "README.md", "# Title\nBody line\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total
        
        assert total.tokensProcessed > 0
        assert total.tokensRaw > total.tokensProcessed  # Экономия токенов
        assert total.savedTokens == total.tokensRaw - total.tokensProcessed
        assert total.savedPct > 0.0
        
        # Адаптер должен записать метрику removed_h1
        assert report.total.metaSummary.get("md.removed_h1", 0) >= 1
    
    def test_md_without_h1_no_savings(self, tmp_path: Path):
        """
        Markdown без H1: адаптер ничего не удаляет → processed == raw.
        """
        create_md_only_project(tmp_path, max_h=2)
        write(tmp_path / "README.md", "Body line\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total
        
        assert total.tokensProcessed > 0
        assert total.tokensProcessed == total.tokensRaw
        assert total.savedTokens == 0


class TestRenderingOverhead:
    """Тесты оверхедов от рендеринга (fences, file markers)."""
    
    def test_md_only_no_overhead(self, tmp_path: Path):
        """
        Markdown-only рендер (без code fence) → renderedOverheadTokens == 0.
        """
        create_md_only_project(tmp_path, max_h=2)
        write(tmp_path / "README.md", "Body line\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total
        
        assert total.renderedTokens == total.tokensProcessed
        assert total.renderedOverheadTokens == 0
        
        # Контекст не используется (рендерится просто секция)
        assert report.context is None
    
    def test_code_with_fence_adds_overhead(self, tmp_path: Path):
        """
        Для кода появляются ```lang и маркеры файлов → есть оверхед.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "a.py", "print('a')\n")
        write(tmp_path / "b.py", "print('b')\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total
        
        assert total.tokensProcessed > 0
        assert total.renderedTokens >= total.tokensProcessed
        assert total.renderedOverheadTokens > 0
    
    def test_code_has_file_markers_overhead(self, tmp_path: Path):
        """
        Даже для кодового содержимого печатаются маркеры "python:...",
        поэтому оверхед всегда > 0.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "a.py", "print('a')\n")
        write(tmp_path / "b.py", "print('b')\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total
        
        assert total.tokensProcessed > 0
        assert total.renderedTokens >= total.tokensProcessed
        assert total.renderedOverheadTokens > 0


class TestContextTemplateOverhead:
    """Тесты оверхедов шаблонов контекстов."""
    
    def test_context_template_overhead(self, tmp_path: Path):
        """
        Контекст с "клеем" (Intro/Outro): проверяем templateOnlyTokens > 0,
        заполненность финальных полей контекста.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "m.py", "x = 1\n")
        write(tmp_path / "lg-cfg" / "glued.ctx.md", "Intro\n\n${all}\n\nOutro\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("ctx:glued", tmp_path))
        
        ctx = report.context
        
        assert ctx is not None
        assert ctx.templateName == "ctx:glued"
        assert ctx.sectionsUsed == {"sec:all": 1}
        assert isinstance(ctx.finalRenderedTokens, int) and ctx.finalRenderedTokens > 0
        assert isinstance(ctx.templateOnlyTokens, int) and ctx.templateOnlyTokens > 0
        
        # Финальный share должен считаться от finalRenderedTokens
        expected_share = ctx.finalRenderedTokens / report.ctxLimit * 100.0
        assert pytest.approx(ctx.finalCtxShare, rel=1e-6) == expected_share
        
        # Иерархия уровней токенов: processed ≤ rendered ≤ final
        assert report.total.tokensProcessed <= report.total.renderedTokens <= ctx.finalRenderedTokens
    
    def test_template_overhead_percentage(self, tmp_path: Path):
        """
        Проверяет корректность расчета процента оверхеда шаблона.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "m.py", "x = 1\n")
        write(tmp_path / "lg-cfg" / "glued.ctx.md", "Intro text\n\n${all}\n\nOutro text\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("ctx:glued", tmp_path))
        
        ctx = report.context
        
        # templateOverheadPct = (templateOnlyTokens / finalRenderedTokens) * 100
        expected_pct = (ctx.templateOnlyTokens / ctx.finalRenderedTokens) * 100.0
        assert pytest.approx(ctx.templateOverheadPct, rel=1e-6) == expected_pct


class TestPromptShares:
    """Тесты распределения долей в промте."""
    
    def test_prompt_shares_sum_to_100(self, tmp_path: Path):
        """
        Проверяем стабильность распределения вкладов: сумма promptShare ≈ 100%.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "a.py", "print('a')\n")
        write(tmp_path / "b.py", "print('b')\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        shares = sum(f.promptShare for f in report.files)
        
        assert 99.9 <= shares <= 100.1
    
    def test_ctx_share_reflects_window_usage(self, tmp_path: Path):
        """
        Проверяет что ctxShare корректно отражает использование окна.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "a.py", "x = 1\n" * 100)  # Больше контента
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total
        
        # ctxShare = (tokensProcessed / ctxLimit) * 100
        expected_share = (total.tokensProcessed / report.ctxLimit) * 100.0
        assert pytest.approx(total.ctxShare, rel=1e-6) == expected_share


class TestMetaSummary:
    """Тесты агрегации метаданных."""
    
    def test_meta_summary_aggregates_numeric_values(self, tmp_path: Path):
        """
        Проверяет что числовые метаданные правильно агрегируются.
        """
        create_md_only_project(tmp_path, max_h=2, strip_h1=True)
        write(tmp_path / "a.md", "# Title A\nBody\n")
        write(tmp_path / "b.md", "# Title B\nBody\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        # Должно быть 2 удаленных H1
        assert report.total.metaSummary.get("md.removed_h1", 0) == 2
    
    def test_meta_summary_for_mixed_files(self, tmp_path: Path):
        """
        Проверяет агрегацию метаданных для файлов разных типов.
        """
        # Создаем проект с Python и Markdown файлами
        write(
            tmp_path / "lg-cfg" / "sections.yaml",
            """all:
  extensions: [".py", ".md"]
  python:
    skip_trivial_inits: true
  markdown:
    max_heading_level: 2
    strip_h1: true
  filters:
    mode: allow
    allow:
      - "/**"
""",
        )
        
        write(tmp_path / "code.py", "# Python code\ndef foo():\n    pass\n")
        write(tmp_path / "doc.md", "# Documentation\nText\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        # Проверяем что метаданные присутствуют
        assert isinstance(report.total.metaSummary, dict)
        assert len(report.total.metaSummary) > 0


class TestFileStatistics:
    """Тесты статистики на уровне отдельных файлов."""
    
    def test_file_statistics_present(self, tmp_path: Path):
        """Проверяет наличие статистики для каждого файла."""
        create_py_only_project(tmp_path)
        write(tmp_path / "a.py", "x = 1\n")
        write(tmp_path / "b.py", "y = 2\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        assert len(report.files) == 2
        
        for file_stat in report.files:
            assert file_stat.path in ["a.py", "b.py"]
            assert file_stat.sizeBytes > 0
            assert file_stat.tokensRaw > 0
            assert file_stat.tokensProcessed > 0
            assert 0 <= file_stat.promptShare <= 100
            assert 0 <= file_stat.ctxShare <= 100
    
    def test_file_saved_tokens_calculation(self, tmp_path: Path):
        """
        Проверяет корректность расчета сэкономленных токенов на уровне файла.
        """
        create_md_only_project(tmp_path, max_h=2, strip_h1=True)
        write(tmp_path / "README.md", "# Big Title\nContent here\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        assert len(report.files) == 1
        file_stat = report.files[0]
        
        # savedTokens = tokensRaw - tokensProcessed
        assert file_stat.savedTokens == file_stat.tokensRaw - file_stat.tokensProcessed
        
        # savedPct = (1 - tokensProcessed/tokensRaw) * 100
        if file_stat.tokensRaw > 0:
            expected_pct = (1 - file_stat.tokensProcessed / file_stat.tokensRaw) * 100.0
            assert pytest.approx(file_stat.savedPct, rel=1e-6) == expected_pct
