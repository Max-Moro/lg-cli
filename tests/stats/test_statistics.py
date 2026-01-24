"""
Tests for token statistics calculation.

Rewritten from tests/test_stats.py using new testing
infrastructure.

Verify:
- Correctness of token count for processed files
- Token savings calculation by adapters
- Rendering overheads (fence, file markers)
- Statistics at context level (template overhead)
- Distribution of shares (shares) in prompt
"""

from pathlib import Path
import pytest

from tests.infrastructure import write, write_context, make_run_options, make_engine, create_integration_mode_section
from lg.engine import _parse_target


# ==================== Helpers for creating projects ====================

def create_md_only_project(root: Path, *, max_h: int | None = 2, strip_h1: bool = False) -> None:
    """Creates minimal project with section for markdown files."""
    create_integration_mode_section(root)
    write(
        root / "lg-cfg" / "sections.yaml",
        f"""all:
  extends: ["ai-interaction"]
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
    """Creates minimal project with section for Python files."""
    create_integration_mode_section(root)
    write(
        root / "lg-cfg" / "sections.yaml",
        """all:
  extends: ["ai-interaction"]
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/**"
""",
    )


# ==================== Markdown Optimization Tests ====================

class TestMarkdownOptimizations:
    """Tests for token optimization for Markdown files."""

    def test_md_with_h1_processed_saves_tokens(self, tmp_path: Path):
        """
        For Markdown adapter removes single H1 when group_size=1
        and given max_heading_level, but adds file label.
        May result in slight size increase overall.
        """
        create_md_only_project(tmp_path, max_h=2, strip_h1=True)
        write(tmp_path / "README.md", "# Title\nBody line\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total

        assert total.tokensProcessed > 0
        # With file labels added, processed can be larger than raw
        # but H1 should be removed
        assert report.total.metaSummary.get("md.removed_h1", 0) >= 1
        assert report.total.metaSummary.get("md.file_label_inserted", 0) >= 1

    def test_md_without_h1_no_savings(self, tmp_path: Path):
        """
        Markdown without H1: adapter only adds file label.
        """
        create_md_only_project(tmp_path, max_h=2)
        write(tmp_path / "README.md", "Body line\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total

        assert total.tokensProcessed > 0
        # With file label added, processed > raw
        assert total.tokensProcessed >= total.tokensRaw
        assert report.total.metaSummary.get("md.file_label_inserted", 0) >= 1


class TestRenderingOverhead:
    """Tests for rendering overheads (fences, file markers)."""

    def test_md_only_no_overhead(self, tmp_path: Path):
        """
        Markdown-only render (without code fence) → renderedOverheadTokens == 0.
        """
        create_md_only_project(tmp_path, max_h=2)
        write(tmp_path / "README.md", "Body line\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total

        assert total.renderedTokens == total.tokensProcessed
        assert total.renderedOverheadTokens == 0

        # Context is not used (only section is rendered)
        assert report.context is None

    def test_code_with_fence_adds_overhead(self, tmp_path: Path):
        """
        For code, ```lang and file markers appear → overhead exists.
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
        Even for code content, "python:..." markers are printed,
        so overhead is always > 0.
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
    """Tests for context template overheads."""

    def test_context_template_overhead(self, tmp_path: Path):
        """
        Context with "glue" (Intro/Outro): check templateOnlyTokens > 0,
        context final fields completion.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "m.py", "x = 1\n")
        write_context(tmp_path, "glued", "Intro\n\n${all}\n\nOutro\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("ctx:glued", tmp_path))
        
        ctx = report.context

        assert ctx is not None
        assert ctx.templateName == "ctx:glued"
        assert ctx.sectionsUsed == {"sec:all": 1}
        assert isinstance(ctx.finalRenderedTokens, int) and ctx.finalRenderedTokens > 0
        assert isinstance(ctx.templateOnlyTokens, int) and ctx.templateOnlyTokens > 0

        # Final share should be calculated from finalRenderedTokens
        expected_share = ctx.finalRenderedTokens / report.ctxLimit * 100.0
        assert pytest.approx(ctx.finalCtxShare, rel=1e-6) == expected_share

        # Hierarchy of token levels: processed ≤ rendered ≤ final
        assert report.total.tokensProcessed <= report.total.renderedTokens <= ctx.finalRenderedTokens

    def test_template_overhead_percentage(self, tmp_path: Path):
        """
        Verifies correct calculation of template overhead percentage.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "m.py", "x = 1\n")
        write_context(tmp_path, "glued", "Intro text\n\n${all}\n\nOutro text\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("ctx:glued", tmp_path))
        
        ctx = report.context

        # templateOverheadPct = (templateOnlyTokens / finalRenderedTokens) * 100
        expected_pct = (ctx.templateOnlyTokens / ctx.finalRenderedTokens) * 100.0
        assert pytest.approx(ctx.templateOverheadPct, rel=1e-6) == expected_pct


class TestPromptShares:
    """Tests for share distribution in prompt."""

    def test_prompt_shares_sum_to_100(self, tmp_path: Path):
        """
        Check stability of contribution distribution: sum of promptShare ≈ 100%.
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
        Verifies that ctxShare correctly reflects window usage.
        """
        create_py_only_project(tmp_path)
        write(tmp_path / "a.py", "x = 1\n" * 100)  # More content

        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        total = report.total

        # ctxShare = (tokensProcessed / ctxLimit) * 100
        expected_share = (total.tokensProcessed / report.ctxLimit) * 100.0
        assert pytest.approx(total.ctxShare, rel=1e-6) == expected_share


class TestMetaSummary:
    """Tests for metadata aggregation."""

    def test_meta_summary_aggregates_numeric_values(self, tmp_path: Path):
        """
        Verifies that numeric metadata is correctly aggregated.
        """
        create_md_only_project(tmp_path, max_h=2, strip_h1=True)
        write(tmp_path / "a.md", "# Title A\nBody\n")
        write(tmp_path / "b.md", "# Title B\nBody\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        # Should be 2 removed H1
        assert report.total.metaSummary.get("md.removed_h1", 0) == 2

    def test_meta_summary_for_mixed_files(self, tmp_path: Path):
        """
        Verifies metadata aggregation for files of different types.
        """
        # Create project with Python and Markdown files
        write(
            tmp_path / "lg-cfg" / "sections.yaml",
            """all:
  extensions: [".py", ".md"]
  python:
    skip_trivial_files: true
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
        
        # Check that metadata is present
        assert isinstance(report.total.metaSummary, dict)
        assert len(report.total.metaSummary) > 0


class TestFileStatistics:
    """Tests for per-file statistics."""

    def test_file_statistics_present(self, tmp_path: Path):
        """Verifies presence of statistics for each file."""
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
        Verifies correct calculation of saved tokens at file level.
        savedTokens can be negative if adapter added content (file labels).
        """
        create_md_only_project(tmp_path, max_h=2, strip_h1=True)
        write(tmp_path / "README.md", "# Big Title\nContent here\n")
        
        engine = make_engine(tmp_path, make_run_options())
        report = engine.generate_report(_parse_target("sec:all", tmp_path))
        
        assert len(report.files) == 1
        file_stat = report.files[0]

        # savedTokens = tokensRaw - tokensProcessed (can be negative)
        expected_saved = file_stat.tokensRaw - file_stat.tokensProcessed
        assert file_stat.savedTokens == expected_saved

        # savedPct = (1 - tokensProcessed/tokensRaw) * 100
        if file_stat.tokensRaw > 0:
            expected_pct = (1 - file_stat.tokensProcessed / file_stat.tokensRaw) * 100.0
            assert pytest.approx(file_stat.savedPct, rel=1e-6) == expected_pct

        # With file labels added, savedTokens can be negative
        # (adapter added useful information)
        assert file_stat.savedTokens <= 0  # In this case file label was added
