from __future__ import annotations

from pathlib import Path

import pytest

from lg.config import load_config
from lg.section.model import SectionCfg
from lg.section import SectionLocation
from lg.filtering.manifest import build_section_manifest
from lg.filtering.model import FilterNode
from lg.section_processor import SectionProcessor
from lg.stats import StatsCollector
from lg.template.context import TemplateContext
from lg.template.addressing.types import ResolvedSection
from tests.infrastructure import write, make_run_context, make_run_options


def test_basic_section_manifest(tmp_path: Path):
    """Tests basic functionality of build_section_manifest."""

    # Create file structure
    write(tmp_path / "src" / "main.py", "print('hello')")
    write(tmp_path / "src" / "utils.py", "def helper(): pass")
    write(tmp_path / "tests" / "test_main.py", "def test(): pass")

    # Create section configuration
    write(tmp_path / "lg-cfg" / "sections.yaml", """
py-files:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "src/**"
      - "tests/**"
""")

    # Create execution context
    run_ctx = make_run_context(tmp_path)

    # Create template context
    template_ctx = TemplateContext(run_ctx)

    # Load configuration
    config = load_config(tmp_path)
    section_cfg = config.sections.get("py-files")

    # Create resolved section
    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="py-files"),
        section_config=section_cfg,
        name="py-files"
    )

    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )

    # Check result
    assert manifest.ref.name == "py-files"
    assert len(manifest.files) == 3

    # Check that all files are properly included
    file_paths = {f.rel_path for f in manifest.files}
    assert "src/main.py" in file_paths
    assert "src/utils.py" in file_paths
    assert "tests/test_main.py" in file_paths


def test_conditional_filters(tmp_path: Path):
    """Tests conditional filters functionality."""

    # Create file structure
    write(tmp_path / "src" / "main.py", "print('hello')")
    write(tmp_path / "src" / "test_main.py", "def test(): pass")
    write(tmp_path / "docs" / "readme.md", "# README")

    # Create configuration with conditional filters
    write(tmp_path / "lg-cfg" / "sections.yaml", """
all-files:
  extensions: [".py", ".md"]
  filters:
    mode: allow
    allow:
      - "src/**"
      - "docs/**"
    when:
      - condition: "tag:tests"
        allow:
          - "**/*test*.py"
      - condition: "NOT tag:tests"
        block:
          - "**/*test*.py"
""")

    # Test 1: without tests tag - test files should be blocked
    run_ctx = make_run_context(tmp_path)
    template_ctx = TemplateContext(run_ctx)

    config = load_config(tmp_path)
    section_cfg = config.sections.get("all-files")

    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="all-files"),
        section_config=section_cfg,
        name="all-files"
    )

    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )

    file_paths = {f.rel_path for f in manifest.files}
    assert "src/main.py" in file_paths
    assert "src/test_main.py" not in file_paths  # Blocked by conditional filter
    assert "docs/readme.md" in file_paths

    # Test 2: with tests tag - test files should be included
    options = make_run_options(extra_tags={"tests"})
    run_ctx = make_run_context(tmp_path, options=options)
    template_ctx = TemplateContext(run_ctx)

    config = load_config(tmp_path)
    section_cfg = config.sections.get("all-files")

    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="all-files"),
        section_config=section_cfg,
        name="all-files"
    )

    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )

    file_paths = {f.rel_path for f in manifest.files}
    assert "src/main.py" in file_paths
    assert "src/test_main.py" in file_paths  # Allowed by conditional filter
    assert "docs/readme.md" in file_paths


def test_gitignore_still_filters_regular_sections(tmp_path: Path):
    """Tests that .gitignore filtering works normally for non-single-file sections."""

    # Initialize git repository so gitignore service works
    write(tmp_path / ".git" / "config", "[core]")

    # Create files with gitignore
    write(tmp_path / ".gitignore", "*.bak\ntemp/\nbuild/\n")
    write(tmp_path / "src" / "main.py", "print('hello')")
    write(tmp_path / "src" / "backup.bak", "backup content")
    write(tmp_path / "temp" / "debug.py", "debug code")
    write(tmp_path / "build" / "output.py", "generated code")
    write(tmp_path / "test.py", "test code")

    # Create regular section (not single-file)
    write(tmp_path / "lg-cfg" / "sections.yaml", """
multi-file:
  extensions: [".py", ".bak"]
  filters:
    mode: allow
    allow:
      - "/src/**"
      - "/test.py"

multi-pattern:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/src/main.py"
      - "/temp/debug.py"

wildcard-pattern:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "/**/*.py"
""")

    run_ctx = make_run_context(tmp_path)
    template_ctx = TemplateContext(run_ctx)
    cfg = load_config(tmp_path)

    # Test 1: Multi-file section with multiple allow patterns
    section_cfg1 = cfg.sections["multi-file"]
    resolved1 = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="multi-file"),
        section_config=section_cfg1,
        name="multi-file"
    )
    manifest = build_section_manifest(
        resolved=resolved1,
        section_config=section_cfg1,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )

    file_paths = [f.rel_path for f in manifest.files]
    assert "src/main.py" in file_paths
    assert "test.py" in file_paths
    assert "src/backup.bak" not in file_paths, ".bak files should be gitignored"

    # Test 2: Section with multiple specific patterns
    section_cfg2 = cfg.sections["multi-pattern"]
    resolved2 = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="multi-pattern"),
        section_config=section_cfg2,
        name="multi-pattern"
    )
    manifest2 = build_section_manifest(
        resolved=resolved2,
        section_config=section_cfg2,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )

    file_paths2 = [f.rel_path for f in manifest2.files]
    assert "src/main.py" in file_paths2
    assert "temp/debug.py" not in file_paths2, "temp/ directory should be gitignored"

    # Test 3: Section with wildcard pattern
    section_cfg3 = cfg.sections["wildcard-pattern"]
    resolved3 = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="wildcard-pattern"),
        section_config=section_cfg3,
        name="wildcard-pattern"
    )
    manifest3 = build_section_manifest(
        resolved=resolved3,
        section_config=section_cfg3,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )

    file_paths3 = [f.rel_path for f in manifest3.files]
    assert "src/main.py" in file_paths3
    assert "test.py" in file_paths3
    assert "temp/debug.py" not in file_paths3, "gitignore should still apply with wildcards"
    assert "build/output.py" not in file_paths3, "gitignore should still apply with wildcards"


def test_local_files_flag_in_manifest(tmp_path: Path):
    """Tests that is_local_files flag is correctly set based on .gitignore."""
    # Initialize git repository so gitignore service works
    write(tmp_path / ".git" / "config", "[core]")

    # Create .gitignore that blocks certain patterns
    write(tmp_path / ".gitignore", """
# Local workspace files
*.local.yaml
.workspace/
my-local-config.yaml
""")

    # Create test files
    write(tmp_path / "normal.yaml", "config: normal")
    write(tmp_path / "file.local.yaml", "config: local")
    write(tmp_path / "my-local-config.yaml", "config: personal")
    write(tmp_path / ".workspace" / "settings.yaml", "settings: workspace")
    write(tmp_path / "public.md", "# Public doc")

    # Create sections with different gitignore interactions
    write(tmp_path / "lg-cfg" / "sections.yaml", """
# Section with gitignored files - should have is_local_files=True
gitignored-single:
  extensions: [".yaml"]
  filters:
    mode: allow
    allow:
      - "/my-local-config.yaml"

gitignored-pattern:
  extensions: [".yaml"]
  filters:
    mode: allow
    allow:
      - "/*.local.yaml"

gitignored-dir:
  extensions: [".yaml"]
  filters:
    mode: allow
    allow:
      - "/.workspace/**"

# Section with NON-gitignored files - should have is_local_files=False
normal-section:
  extensions: [".yaml"]
  filters:
    mode: allow
    allow:
      - "/normal.yaml"

normal-multi:
  extensions: [".yaml", ".md"]
  filters:
    mode: allow
    allow:
      - "/normal.yaml"
      - "/public.md"

# Section with wildcards on normal files - should have is_local_files=False
normal-wildcard:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/*.md"
""")

    run_ctx = make_run_context(tmp_path)
    template_ctx = TemplateContext(run_ctx)
    cfg = load_config(tmp_path)

    # Test 1: Single gitignored file - should have is_local_files=True
    section_cfg = cfg.sections["gitignored-single"]
    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="gitignored-single"),
        section_config=section_cfg,
        name="gitignored-single"
    )
    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is True, "Gitignored single-file section should have is_local_files=True"

    # Test 2: Gitignored pattern - should have is_local_files=True
    section_cfg = cfg.sections["gitignored-pattern"]
    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="gitignored-pattern"),
        section_config=section_cfg,
        name="gitignored-pattern"
    )
    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is True, "Gitignored pattern section should have is_local_files=True"

    # Test 3: Gitignored directory - should have is_local_files=True
    section_cfg = cfg.sections["gitignored-dir"]
    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="gitignored-dir"),
        section_config=section_cfg,
        name="gitignored-dir"
    )
    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is True, "Gitignored directory section should have is_local_files=True"

    # Test 4: Normal single-file section - should have is_local_files=False
    section_cfg = cfg.sections["normal-section"]
    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="normal-section"),
        section_config=section_cfg,
        name="normal-section"
    )
    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is False, "Non-gitignored single-file section should have is_local_files=False"

    # Test 5: Normal multi-file section - should have is_local_files=False
    section_cfg = cfg.sections["normal-multi"]
    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="normal-multi"),
        section_config=section_cfg,
        name="normal-multi"
    )
    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is False, "Non-gitignored multi-file section should have is_local_files=False"

    # Test 6: Normal wildcard section - should have is_local_files=False
    section_cfg = cfg.sections["normal-wildcard"]
    resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="normal-wildcard"),
        section_config=section_cfg,
        name="normal-wildcard"
    )
    manifest = build_section_manifest(
        resolved=resolved,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is False, "Non-gitignored wildcard section should have is_local_files=False"


def test_virtual_section_local_files_no_error(tmp_path: Path):
    """Tests that virtual sections for local files don't error when files are missing."""
    # Initialize git repository so gitignore service works
    write(tmp_path / ".git" / "config", "[core]")

    # Create empty directory structure (no actual files)
    write(tmp_path / "lg-cfg" / "sections.yaml", """
dummy:
  extensions: [".py"]
  filters:
    mode: block
""")

    # Create .gitignore to make the single file truly "local"
    write(tmp_path / ".gitignore", """
# Local workspace configuration
my-local-config.yaml
""")

    # Create context
    run_ctx = make_run_context(tmp_path)

    # Create stats collector
    stats_collector = StatsCollector(128000, run_ctx.tokenizer)

    # Create section processor
    processor = SectionProcessor(run_ctx, stats_collector)

    # Create template context with virtual section for local file
    template_ctx = TemplateContext(run_ctx)

    # Create virtual section that describes a single local file (that doesn't exist)
    virtual_section_cfg = SectionCfg(
        extensions=[".yaml"],
        filters=FilterNode(
            mode="allow",
            allow=["/my-local-config.yaml"]
        )
    )

    # Process section - should NOT raise error for missing local file
    virtual_resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="virtual"),
        section_config=virtual_section_cfg,
        name="virtual"
    )

    # This should not raise RuntimeError about missing files
    rendered = processor.process_section(virtual_resolved, template_ctx)

    # Verify the section was processed (even though no files exist)
    assert rendered.ref.name == "virtual"
    assert rendered.files == []  # No files, but no error
    assert rendered.text == ""  # Empty content is OK for local files

    # Now test with non-local virtual section (should still error)
    # Virtual section (not local files)
    non_local_virtual = SectionCfg(
        extensions=[".md"],
        filters=FilterNode(
            mode="allow",
            allow=["/example-config.yaml"]
        )
    )

    # Create another resolved section for the non-local test
    non_local_resolved = ResolvedSection(
        scope_dir=tmp_path,
        scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="md:example-config.yaml"),
        section_config=non_local_virtual,
        name="md:example-config.yaml"
    )

    # This SHOULD raise RuntimeError about missing files
    with pytest.raises(RuntimeError) as exc_info:
        processor.process_section(non_local_resolved, template_ctx)

    assert "No markdown files found" in str(exc_info.value)