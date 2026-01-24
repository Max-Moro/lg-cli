from __future__ import annotations

from pathlib import Path

from lg.section_processor import SectionProcessor
from lg.stats.collector import StatsCollector
from lg.template.context import TemplateContext
from lg.addressing import SECTION_CONFIG
from lg.adaptive.context_resolver import ContextResolver
from lg.section import SectionService

from tests.infrastructure import make_run_context, make_run_options, create_integration_mode_section


def _write(tmp: Path, rel: str, text: str = "x") -> Path:
    p = tmp / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _write_sections_yaml(tmp: Path, text: str) -> Path:
    p = tmp / "lg-cfg" / "sections.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def test_section_processor_integration(tmp_path: Path):
    """Tests integration of section_processor with manifest.builder."""

    # Create file structure
    _write(tmp_path, "src/main.py", 'print("hello world")')
    _write(tmp_path, "src/utils.py", 'def helper():\n    return "test"')

    # Create section configuration
    _write_sections_yaml(tmp_path, """
py-files:
  extensions: [".py"]
  skip_empty: true
  filters:
    mode: allow
    allow:
      - "src/**"
""")

    # Create execution context
    run_ctx = make_run_context(tmp_path)

    # Create statistics collector
    stats_collector = StatsCollector(
        128000, run_ctx.tokenizer
    )

    # Create section processor
    section_processor = SectionProcessor(
        run_ctx=run_ctx,
        stats_collector=stats_collector
    )

    # Create template context and resolve section through addressing
    template_ctx = TemplateContext(run_ctx)
    resolved = run_ctx.addressing.resolve("py-files", SECTION_CONFIG)

    # Process section
    rendered_section = section_processor.process_section(resolved, template_ctx)

    # Check result
    assert rendered_section.resolved.name == "py-files"
    assert len(rendered_section.files) == 2
    assert rendered_section.text  # Must not be empty text

    # Check that file contents are in the text
    assert "hello world" in rendered_section.text
    assert "def helper" in rendered_section.text

    # Check files
    file_paths = {f.rel_path for f in rendered_section.files}
    assert "src/main.py" in file_paths
    assert "src/utils.py" in file_paths


def test_section_processor_with_conditional_filters(tmp_path: Path):
    """Tests section_processor with conditional filters."""

    # Create file structure
    _write(tmp_path, "src/main.py", 'print("main")')
    _write(tmp_path, "src/test_main.py", 'def test_main(): pass')
    _write(tmp_path, "docs/readme.md", '# README')

    # Configuration with conditional filter
    _write_sections_yaml(tmp_path, """
all-files:
  extends: ["ai-interaction"]
  extensions: [".py", ".md"]
  filters:
    mode: allow
    allow:
      - "**"
    when:
      - condition: "tag:minimal"
        block:
          - "**/*test*.py"
          - "docs/**"
""")

    # Create integration mode section
    create_integration_mode_section(tmp_path)

    # Test 1: without minimal tag - all files included
    options1 = make_run_options(extra_tags=set())
    run_ctx = make_run_context(tmp_path, options1)
    stats_collector = StatsCollector(128000, run_ctx.tokenizer)
    section_processor = SectionProcessor(run_ctx=run_ctx, stats_collector=stats_collector)

    template_ctx = TemplateContext(run_ctx)

    # Initialize template context with adaptive model
    context_resolver = ContextResolver(
        section_service=SectionService(tmp_path, run_ctx.cache),
        addressing=run_ctx.addressing,
        cfg_root=tmp_path / "lg-cfg"
    )
    adaptive_model = context_resolver.resolve_for_section("all-files", tmp_path)
    template_ctx.reset_for_context(adaptive_model)

    resolved = run_ctx.addressing.resolve("all-files", SECTION_CONFIG)

    rendered_section = section_processor.process_section(resolved, template_ctx)

    file_paths = {f.rel_path for f in rendered_section.files}
    assert len(file_paths) == 3
    assert "src/main.py" in file_paths
    assert "src/test_main.py" in file_paths
    assert "docs/readme.md" in file_paths

    # Test 2: with minimal tag - test files and documentation excluded
    options2 = make_run_options(extra_tags={"minimal"})
    run_ctx = make_run_context(tmp_path, options2)
    stats_collector = StatsCollector(128000, tokenizer=run_ctx.tokenizer)
    section_processor = SectionProcessor(run_ctx=run_ctx, stats_collector=stats_collector)

    template_ctx = TemplateContext(run_ctx)

    # Re-initialize template context with adaptive model for new options
    context_resolver = ContextResolver(
        section_service=SectionService(tmp_path, run_ctx.cache),
        addressing=run_ctx.addressing,
        cfg_root=tmp_path / "lg-cfg"
    )
    adaptive_model = context_resolver.resolve_for_section("all-files", tmp_path)
    template_ctx.reset_for_context(adaptive_model)

    # Need to re-resolve with new context
    resolved = run_ctx.addressing.resolve("all-files", SECTION_CONFIG)

    rendered_section = section_processor.process_section(resolved, template_ctx)

    file_paths = {f.rel_path for f in rendered_section.files}
    assert len(file_paths) == 1
    assert "src/main.py" in file_paths
    assert "src/test_main.py" not in file_paths  # Blocked
    assert "docs/readme.md" not in file_paths    # Blocked
