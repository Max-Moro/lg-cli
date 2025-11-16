from __future__ import annotations

from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.config.adaptive_loader import AdaptiveConfigLoader
from lg.config.adaptive_model import ModeOptions
from lg.run_context import RunContext
from lg.section_processor import SectionProcessor
from lg.stats import TokenService
from lg.stats.collector import StatsCollector
from lg.template.context import TemplateContext
from lg.types import RunOptions, SectionRef
from lg.vcs import NullVcs


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
    run_ctx = _create_run_context(tmp_path)

    # Create statistics collector
    stats_collector = StatsCollector(
        128000, run_ctx.tokenizer
    )

    # Create section processor
    section_processor = SectionProcessor(
        run_ctx=run_ctx,
        stats_collector=stats_collector
    )

    # Create template context and section reference
    template_ctx = TemplateContext(run_ctx)
    section_ref = SectionRef(
        name="py-files",
        scope_rel="",
        scope_dir=tmp_path
    )

    # Process section
    rendered_section = section_processor.process_section(section_ref, template_ctx)

    # Check result
    assert rendered_section.ref == section_ref
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

    # Test 1: without minimal tag - all files included
    run_ctx = _create_run_context(tmp_path, active_tags=set())
    stats_collector = StatsCollector(128000, run_ctx.tokenizer)
    section_processor = SectionProcessor(run_ctx=run_ctx, stats_collector=stats_collector)

    template_ctx = TemplateContext(run_ctx)
    section_ref = SectionRef(name="all-files", scope_rel="", scope_dir=tmp_path)

    rendered_section = section_processor.process_section(section_ref, template_ctx)

    file_paths = {f.rel_path for f in rendered_section.files}
    assert len(file_paths) == 3
    assert "src/main.py" in file_paths
    assert "src/test_main.py" in file_paths
    assert "docs/readme.md" in file_paths

    # Test 2: with minimal tag - test files and documentation excluded
    run_ctx = _create_run_context(tmp_path, active_tags={"minimal"})
    stats_collector = StatsCollector(128000, tokenizer=run_ctx.tokenizer)
    section_processor = SectionProcessor(run_ctx=run_ctx, stats_collector=stats_collector)

    template_ctx = TemplateContext(run_ctx)

    rendered_section = section_processor.process_section(section_ref, template_ctx)

    file_paths = {f.rel_path for f in rendered_section.files}
    assert len(file_paths) == 1
    assert "src/main.py" in file_paths
    assert "src/test_main.py" not in file_paths  # Blocked
    assert "docs/readme.md" not in file_paths    # Blocked


def _create_run_context(root: Path, active_tags: set | None = None) -> RunContext:
    """Helper function to create RunContext."""
    if active_tags is None:
        active_tags = set()
    
    tool_ver = "0.3.0"
    cache = Cache(root, enabled=None, fresh=False, tool_version=tool_ver)
    vcs = NullVcs()
    tokenizer = TokenService(root, "tiktoken", "cl100k_base", cache=cache)
    adaptive_loader = AdaptiveConfigLoader(root)
    
    return RunContext(
        root=root,
        options=RunOptions(),
        cache=cache,
        vcs=vcs,
        tokenizer=tokenizer,
        adaptive_loader=adaptive_loader,
        mode_options=ModeOptions(),
        active_tags=active_tags
    )