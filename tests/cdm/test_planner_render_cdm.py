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
    Хелпер для полной обработки секции в новом пайплайне V2:
    manifest -> plan -> process -> render
    
    Returns:
        Tuple (manifest, plan, rendered_section)
    """
    rc = mk_run_ctx(root)
    template_ctx = TemplateContext(rc)
    
    # Определяем scope_dir на основе scope_rel
    if scope_rel:
        scope_dir = (root / scope_rel).resolve()
    else:
        scope_dir = root
    
    section_ref = SectionRef(
        name=section_name,
        scope_rel=scope_rel,
        scope_dir=scope_dir
    )
    
    # 1. Строим манифест
    config = load_config(scope_dir)
    section_cfg = config.sections.get(section_ref.name)
    
    manifest = build_section_manifest(
        section_ref=section_ref,
        section_config=section_cfg,
        template_ctx=template_ctx,
        root=root,
        vcs=vcs or rc.vcs,
        vcs_mode=vcs_mode
    )
    
    # 2. Строим план
    plan = build_section_plan(manifest, template_ctx)
    
    # 3. Обрабатываем файлы
    processed_files = process_files(plan, template_ctx)
    
    # 4. Рендерим
    rendered_section = render_section(plan, processed_files)
    
    return manifest, plan, rendered_section


def test_planner_and_render_for_addressed_sections(monorepo: Path):
    """
    Проверяем работу полного пайплайна V2 для CDM секций:
      • для секции packages/svc-a::a — use_fence=True, есть группы python и '' (md),
        рендер содержит ```python и FILE-маркер с укороченной меткой README.md
      • для секции apps/web::web-api — use_fence=False, рендер без FILE-маркеров
    """
    # Тестируем секцию 'a' из скоупа 'packages/svc-a'
    manifest_a, plan_a, rendered_a = _process_section(monorepo, "a", "packages/svc-a")
    
    # Проверяем свойства плана секции A
    assert plan_a.use_fence is True
    langs = {f.language_hint for f in plan_a.files}
    assert "python" in langs and "markdown" in langs  # есть и код, и markdown-файлы
    
    # Проверяем рендер секции A
    txt_a = rendered_a.text
    assert "```python:packages/svc-a/src/other/y.py" in txt_a
    # README.md теперь в fence-блоке
    assert "```markdown:packages/svc-a/README.md" in txt_a

    # Тестируем секцию 'web-api' из скоупа 'apps/web'
    manifest_web, plan_web, rendered_web = _process_section(monorepo, "web-api", "apps/web")
    
    # Секция web-api — чистый MD без fenced
    assert plan_web.use_fence is False
    
    # Проверяем рендер секции web-api
    txt_web = rendered_web.text
    assert "```" not in txt_web
    assert "# web docs" in txt_web  # содержимое apps/web/docs/index.md
    
    # Дополнительные проверки для CDM
    assert manifest_a.ref.scope_rel == "packages/svc-a"
    assert manifest_a.ref.name == "a"
    assert manifest_web.ref.scope_rel == "apps/web"
    assert manifest_web.ref.name == "web-api"
