from __future__ import annotations

from pathlib import Path

from lg.adapters.processor import process_files
from lg.filtering.manifest import build_section_manifest
from lg.config import load_config
from lg.rendering.planner import build_section_plan
from lg.rendering.renderer import render_section
from lg.template.context import TemplateContext
from lg.types import SectionRef
from .conftest import mk_run_ctx


def _process_section(
    root: Path,
    section_name: str,
    scope_rel: str = "",
    *,
    vcs_mode: str = "all",
    vcs=None
):
    """
    Helper for full section processing in the new V2 pipeline:
    manifest -> plan -> process -> render

    Returns:
        Tuple (manifest, plan, rendered_section)
    """
    rc = mk_run_ctx(root)
    template_ctx = TemplateContext(rc)

    # Determine scope_dir based on scope_rel
    if scope_rel:
        scope_dir = (root / scope_rel).resolve()
    else:
        scope_dir = root

    section_ref = SectionRef(
        name=section_name,
        scope_rel=scope_rel,
        scope_dir=scope_dir
    )

    # 1. Build manifest
    config = load_config(scope_dir)
    section_cfg = config.sections.get(section_ref.name)

    manifest = build_section_manifest(
        section_ref=section_ref,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=root,
        vcs=vcs or rc.vcs,
        gitignore_service=rc.gitignore,
        vcs_mode=vcs_mode
    )

    # 2. Build plan
    plan = build_section_plan(manifest, template_ctx)

    # 3. Process files
    processed_files = process_files(plan, template_ctx)

    # 4. Render
    rendered_section = render_section(plan, processed_files)

    return manifest, plan, rendered_section


def test_planner_and_render_for_addressed_sections(monorepo: Path):
    """
    Verify full V2 pipeline for CDM sections:
      • for section packages/svc-a::a — use_fence=True, has groups python and '' (md),
        render contains ```python and FILE-marker with shortened label README.md
      • for section apps/web::web-api — use_fence=False, render without FILE-markers
    """
    # Test section 'a' from scope 'packages/svc-a'
    manifest_a, plan_a, rendered_a = _process_section(monorepo, "a", "packages/svc-a")

    # Check plan properties for section A
    assert plan_a.use_fence is True
    langs = {f.language_hint for f in plan_a.files}
    assert "python" in langs and "markdown" in langs  # has both code and markdown files

    # Check render for section A
    txt_a = rendered_a.text
    assert "```python:packages/svc-a/src/other/y.py" in txt_a
    # README.md now in fence-block
    assert "```markdown:packages/svc-a/README.md" in txt_a

    # Test section 'web-api' from scope 'apps/web'
    manifest_web, plan_web, rendered_web = _process_section(monorepo, "web-api", "apps/web")

    # Section web-api — pure MD without fences
    assert plan_web.use_fence is False

    # Check render for section web-api
    txt_web = rendered_web.text
    assert "```" not in txt_web
    assert "# web docs" in txt_web  # content from apps/web/docs/index.md

    # Additional checks for CDM
    assert manifest_a.ref.scope_rel == "packages/svc-a"
    assert manifest_a.ref.name == "a"
    assert manifest_web.ref.scope_rel == "apps/web"
    assert manifest_web.ref.name == "web-api"
