from __future__ import annotations

from pathlib import Path

import pytest

from lg.config import load_config
from lg.config.model import SectionCfg
from lg.filtering.manifest import build_section_manifest
from lg.filtering.model import FilterNode
from lg.section_processor import SectionProcessor
from lg.stats import StatsCollector
from lg.template.context import TemplateContext
from lg.types import SectionRef
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

    # Create section reference
    section_ref = SectionRef(
        name="py-files",
        scope_rel="",
        scope_dir=tmp_path
    )

    # Load configuration and build manifest
    config = load_config(tmp_path)
    section_cfg = config.sections.get(section_ref.name)

    manifest = build_section_manifest(
        section_ref=section_ref,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )

    # Check result
    assert manifest.ref == section_ref
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

    section_ref = SectionRef(name="all-files", scope_rel="", scope_dir=tmp_path)

    config = load_config(tmp_path)
    section_cfg = config.sections.get(section_ref.name)

    manifest = build_section_manifest(
        section_ref=section_ref,
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
    section_cfg = config.sections.get(section_ref.name)

    manifest = build_section_manifest(
        section_ref=section_ref,
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
    section_ref = SectionRef("multi-file", "", tmp_path)
    manifest = build_section_manifest(
        section_ref=section_ref,
        section_config=cfg.sections["multi-file"],
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
    section_ref2 = SectionRef("multi-pattern", "", tmp_path)
    manifest2 = build_section_manifest(
        section_ref=section_ref2,
        section_config=cfg.sections["multi-pattern"],
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
    section_ref3 = SectionRef("wildcard-pattern", "", tmp_path)
    manifest3 = build_section_manifest(
        section_ref=section_ref3,
        section_config=cfg.sections["wildcard-pattern"],
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
    manifest = build_section_manifest(
        section_ref=SectionRef("gitignored-single", "", tmp_path),
        section_config=cfg.sections["gitignored-single"],
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is True, "Gitignored single-file section should have is_local_files=True"

    # Test 2: Gitignored pattern - should have is_local_files=True
    manifest = build_section_manifest(
        section_ref=SectionRef("gitignored-pattern", "", tmp_path),
        section_config=cfg.sections["gitignored-pattern"],
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is True, "Gitignored pattern section should have is_local_files=True"

    # Test 3: Gitignored directory - should have is_local_files=True
    manifest = build_section_manifest(
        section_ref=SectionRef("gitignored-dir", "", tmp_path),
        section_config=cfg.sections["gitignored-dir"],
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is True, "Gitignored directory section should have is_local_files=True"

    # Test 4: Normal single-file section - should have is_local_files=False
    manifest = build_section_manifest(
        section_ref=SectionRef("normal-section", "", tmp_path),
        section_config=cfg.sections["normal-section"],
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is False, "Non-gitignored single-file section should have is_local_files=False"

    # Test 5: Normal multi-file section - should have is_local_files=False
    manifest = build_section_manifest(
        section_ref=SectionRef("normal-multi", "", tmp_path),
        section_config=cfg.sections["normal-multi"],
        template_ctx=template_ctx,
        root=tmp_path,
        vcs=run_ctx.vcs,
        gitignore_service=run_ctx.gitignore,
        vcs_mode="all",
        target_branch=None
    )
    assert manifest.is_local_files is False, "Non-gitignored multi-file section should have is_local_files=False"

    # Test 6: Normal wildcard section - should have is_local_files=False
    manifest = build_section_manifest(
        section_ref=SectionRef("normal-wildcard", "", tmp_path),
        section_config=cfg.sections["normal-wildcard"],
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

    # Set up virtual section that describes a single local file (that doesn't exist)
    virtual_section = SectionCfg(
        extensions=[".yaml"],
        filters=FilterNode(
            mode="allow",
            allow=["/my-local-config.yaml"]
        )
    )
    template_ctx.set_virtual_section(virtual_section)

    # Process section - should NOT raise error for missing local file
    section_ref = SectionRef("virtual", "", tmp_path)

    # This should not raise RuntimeError about missing files
    rendered = processor.process_section(section_ref, template_ctx)

    # Verify the section was processed (even though no files exist)
    assert rendered.ref == section_ref
    assert rendered.files == []  # No files, but no error
    assert rendered.text == ""  # Empty content is OK for local files

    # Now test with non-local virtual section (should still error)
    template_ctx.clear_virtual_section()

    # Virtual section (not local files)
    non_local_virtual = SectionCfg(
        extensions=[".md"],
        filters=FilterNode(
            mode="allow",
            allow=["/example-config.yaml"]
        )
    )
    template_ctx.set_virtual_section(non_local_virtual)

    # This SHOULD raise RuntimeError about missing files
    with pytest.raises(RuntimeError) as exc_info:
        processor.process_section(section_ref, template_ctx)

    assert "No markdown files found" in str(exc_info.value)