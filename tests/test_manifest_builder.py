from __future__ import annotations

from pathlib import Path

import pytest

from lg.section.model import SectionCfg
from lg.section import SectionLocation
from lg.filtering.manifest import build_section_manifest
from lg.filtering.model import FilterNode
from lg.section_processor import SectionProcessor
from lg.stats import StatsCollector
from lg.template.context import TemplateContext
from lg.addressing.types import ResolvedSection
from lg.adaptive.context_resolver import ContextResolver
from lg.section import SectionService
from tests.infrastructure import write, make_run_context, make_run_options, load_sections, create_integration_mode_section


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

    # Load sections
    sections = load_sections(tmp_path)
    section_cfg = sections.get("py-files")

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
    assert manifest.resolved.name == "py-files"
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

    # Create integration mode section first
    create_integration_mode_section(tmp_path)

    # Create configuration with conditional filters
    write(tmp_path / "lg-cfg" / "sections.yaml", """
all-files:
  extends: ["ai-interaction"]
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

    # Initialize template context with adaptive model
    context_resolver = ContextResolver(
        section_service=SectionService(tmp_path, run_ctx.cache),
        addressing=run_ctx.addressing,
        cfg_root=tmp_path / "lg-cfg"
    )
    adaptive_model = context_resolver.resolve_for_section("all-files", tmp_path)
    template_ctx.reset_for_context(adaptive_model)

    sections = load_sections(tmp_path)
    section_cfg = sections.get("all-files")

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

    # Initialize template context with adaptive model
    context_resolver = ContextResolver(
        section_service=SectionService(tmp_path, run_ctx.cache),
        addressing=run_ctx.addressing,
        cfg_root=tmp_path / "lg-cfg"
    )
    adaptive_model = context_resolver.resolve_for_section("all-files", tmp_path)
    template_ctx.reset_for_context(adaptive_model)

    sections = load_sections(tmp_path)
    section_cfg = sections.get("all-files")

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
    sections = load_sections(tmp_path)

    # Test 1: Multi-file section with multiple allow patterns
    section_cfg1 = sections["multi-file"]
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
    section_cfg2 = sections["multi-pattern"]
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
    section_cfg3 = sections["wildcard-pattern"]
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
    sections = load_sections(tmp_path)

    # Test 1: Single gitignored file - should have is_local_files=True
    section_cfg = sections["gitignored-single"]
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
    section_cfg = sections["gitignored-pattern"]
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
    section_cfg = sections["gitignored-dir"]
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
    section_cfg = sections["normal-section"]
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
    section_cfg = sections["normal-multi"]
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
    section_cfg = sections["normal-wildcard"]
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
    assert rendered.resolved.name == "virtual"
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


# ---- Tests for when: conditions in targets ---- #

def test_when_in_targets_basic(tmp_path: Path):
    """Target with when: condition applies overrides only when condition is met."""
    write(tmp_path / "src" / "engine.py", "def run(): pass")
    write(tmp_path / "src" / "utils.py", "def helper(): pass")

    write(tmp_path / "lg-cfg" / "sections.yaml", """
code:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "src/**"
  targets:
    - match: "/src/engine.py"
      python:
        when:
          - condition: "tag:review"
            strip_function_bodies: true
""")

    sections = load_sections(tmp_path)
    section_cfg = sections["code"]
    resolved = ResolvedSection(
        scope_dir=tmp_path, scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="code"),
        section_config=section_cfg, name="code"
    )

    # Without review tag: no strip_function_bodies override
    run_ctx = make_run_context(tmp_path)
    template_ctx = TemplateContext(run_ctx)
    manifest = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx, root=tmp_path,
        vcs=run_ctx.vcs, gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )
    engine_file = next(f for f in manifest.files if f.rel_path == "src/engine.py")
    py_overrides = engine_file.adapter_overrides.get("python", {})
    assert "strip_function_bodies" not in py_overrides

    # With review tag: strip_function_bodies should be set
    run_ctx2 = make_run_context(tmp_path, options=make_run_options(extra_tags={"review"}))
    template_ctx2 = TemplateContext(run_ctx2)
    manifest2 = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx2, root=tmp_path,
        vcs=run_ctx2.vcs, gitignore_service=run_ctx2.gitignore,
        vcs_mode="all"
    )
    engine_file2 = next(f for f in manifest2.files if f.rel_path == "src/engine.py")
    py_overrides2 = engine_file2.adapter_overrides.get("python", {})
    assert py_overrides2.get("strip_function_bodies") is True

    # Unmatched file should have no overrides regardless of tag
    utils_file = next(f for f in manifest2.files if f.rel_path == "src/utils.py")
    assert not utils_file.adapter_overrides.get("python", {})


def test_when_in_targets_backward_compat(tmp_path: Path):
    """Targets without when: work exactly as before."""
    write(tmp_path / "src" / "main.py", "def main(): pass")

    write(tmp_path / "lg-cfg" / "sections.yaml", """
code:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "src/**"
  targets:
    - match: "/src/main.py"
      python:
        strip_function_bodies: true
        comment_policy: "keep_doc"
""")

    sections = load_sections(tmp_path)
    section_cfg = sections["code"]
    resolved = ResolvedSection(
        scope_dir=tmp_path, scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="code"),
        section_config=section_cfg, name="code"
    )

    run_ctx = make_run_context(tmp_path)
    template_ctx = TemplateContext(run_ctx)
    manifest = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx, root=tmp_path,
        vcs=run_ctx.vcs, gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )

    main_file = next(f for f in manifest.files if f.rel_path == "src/main.py")
    py_overrides = main_file.adapter_overrides.get("python", {})
    assert py_overrides["strip_function_bodies"] is True
    assert py_overrides["comment_policy"] == "keep_doc"


def test_when_in_targets_multiple_conditions(tmp_path: Path):
    """Multiple when: items — later matching conditions override earlier ones."""
    write(tmp_path / "src" / "core.py", "class Core: pass")

    write(tmp_path / "lg-cfg" / "sections.yaml", """
code:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "src/**"
  targets:
    - match: "/src/core.py"
      python:
        when:
          - condition: "tag:optimize"
            strip_function_bodies: true
            comment_policy: "keep_doc"
          - condition: "tag:optimize AND tag:aggressive"
            comment_policy: "strip_all"
""")

    sections = load_sections(tmp_path)
    section_cfg = sections["code"]
    resolved = ResolvedSection(
        scope_dir=tmp_path, scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="code"),
        section_config=section_cfg, name="code"
    )

    # Only optimize tag: first condition applies
    run_ctx = make_run_context(tmp_path, options=make_run_options(extra_tags={"optimize"}))
    template_ctx = TemplateContext(run_ctx)
    manifest = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx, root=tmp_path,
        vcs=run_ctx.vcs, gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )
    core_file = next(f for f in manifest.files if f.rel_path == "src/core.py")
    py = core_file.adapter_overrides.get("python", {})
    assert py["strip_function_bodies"] is True
    assert py["comment_policy"] == "keep_doc"

    # Both tags: second condition overrides comment_policy
    run_ctx2 = make_run_context(tmp_path, options=make_run_options(extra_tags={"optimize", "aggressive"}))
    template_ctx2 = TemplateContext(run_ctx2)
    manifest2 = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx2, root=tmp_path,
        vcs=run_ctx2.vcs, gitignore_service=run_ctx2.gitignore,
        vcs_mode="all"
    )
    core_file2 = next(f for f in manifest2.files if f.rel_path == "src/core.py")
    py2 = core_file2.adapter_overrides.get("python", {})
    assert py2["strip_function_bodies"] is True
    assert py2["comment_policy"] == "strip_all"


def test_when_in_targets_mixed_base_and_conditional(tmp_path: Path):
    """Target has both unconditional base options and conditional when: options."""
    write(tmp_path / "src" / "api.py", "def endpoint(): pass")

    write(tmp_path / "lg-cfg" / "sections.yaml", """
code:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "src/**"
  targets:
    - match: "/src/api.py"
      python:
        comment_policy: "keep_doc"
        when:
          - condition: "tag:compact"
            strip_function_bodies: true
""")

    sections = load_sections(tmp_path)
    section_cfg = sections["code"]
    resolved = ResolvedSection(
        scope_dir=tmp_path, scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="code"),
        section_config=section_cfg, name="code"
    )

    # Without compact tag: only base options apply
    run_ctx = make_run_context(tmp_path)
    template_ctx = TemplateContext(run_ctx)
    manifest = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx, root=tmp_path,
        vcs=run_ctx.vcs, gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )
    api_file = next(f for f in manifest.files if f.rel_path == "src/api.py")
    py = api_file.adapter_overrides.get("python", {})
    assert py["comment_policy"] == "keep_doc"
    assert "strip_function_bodies" not in py

    # With compact tag: base + conditional options
    run_ctx2 = make_run_context(tmp_path, options=make_run_options(extra_tags={"compact"}))
    template_ctx2 = TemplateContext(run_ctx2)
    manifest2 = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx2, root=tmp_path,
        vcs=run_ctx2.vcs, gitignore_service=run_ctx2.gitignore,
        vcs_mode="all"
    )
    api_file2 = next(f for f in manifest2.files if f.rel_path == "src/api.py")
    py2 = api_file2.adapter_overrides.get("python", {})
    assert py2["comment_policy"] == "keep_doc"
    assert py2["strip_function_bodies"] is True


def test_when_in_targets_not_condition(tmp_path: Path):
    """NOT condition disables optimization when tag is active."""
    write(tmp_path / "src" / "engine.py", "def run(): pass")

    write(tmp_path / "lg-cfg" / "sections.yaml", """
code:
  extensions: [".py"]
  filters:
    mode: allow
    allow:
      - "src/**"
  targets:
    - match: "/src/engine.py"
      python:
        when:
          - condition: "NOT tag:review"
            strip_function_bodies: true
            comment_policy: "keep_doc"
""")

    sections = load_sections(tmp_path)
    section_cfg = sections["code"]
    resolved = ResolvedSection(
        scope_dir=tmp_path, scope_rel="",
        location=SectionLocation(file_path=Path("test"), local_name="code"),
        section_config=section_cfg, name="code"
    )

    # Without review tag: NOT tag:review is true → optimizations active
    run_ctx = make_run_context(tmp_path)
    template_ctx = TemplateContext(run_ctx)
    manifest = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx, root=tmp_path,
        vcs=run_ctx.vcs, gitignore_service=run_ctx.gitignore,
        vcs_mode="all"
    )
    engine_file = next(f for f in manifest.files if f.rel_path == "src/engine.py")
    py = engine_file.adapter_overrides.get("python", {})
    assert py["strip_function_bodies"] is True
    assert py["comment_policy"] == "keep_doc"

    # With review tag: NOT tag:review is false → no overrides
    run_ctx2 = make_run_context(tmp_path, options=make_run_options(extra_tags={"review"}))
    template_ctx2 = TemplateContext(run_ctx2)
    manifest2 = build_section_manifest(
        resolved=resolved, section_config=section_cfg,
        template_ctx=template_ctx2, root=tmp_path,
        vcs=run_ctx2.vcs, gitignore_service=run_ctx2.gitignore,
        vcs_mode="all"
    )
    engine_file2 = next(f for f in manifest2.files if f.rel_path == "src/engine.py")
    py2 = engine_file2.adapter_overrides.get("python", {})
    assert "strip_function_bodies" not in py2
    assert "comment_policy" not in py2