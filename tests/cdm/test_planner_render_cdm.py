from __future__ import annotations

from pathlib import Path

from lg.adapters.processor import process_files
from lg.manifest.builder import build_section_manifest_from_config
from lg.config import load_config
from lg.plan.planner import build_section_plan
from lg.render.renderer import render_section
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
    
    manifest = build_section_manifest_from_config(
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
      • для секции apps/web::web-api — md_only=True, use_fence=False, рендер без FILE-маркеров
    """
    # Тестируем секцию 'a' из скоупа 'packages/svc-a'
    manifest_a, plan_a, rendered_a = _process_section(monorepo, "a", "packages/svc-a")
    
    # Проверяем свойства плана секции A
    assert plan_a.use_fence is True and plan_a.md_only is False
    langs = {g.lang for g in plan_a.groups}
    assert "python" in langs and "" in langs  # есть и код, и markdown-группа
    
    # Проверяем рендер секции A
    txt_a = rendered_a.text
    assert "```python" in txt_a
    # метка README должна быть короткой (auto снимает общий префикс)
    assert "# —— FILE: README.md ——" in txt_a or "# —— FILE: packages/svc-a/README.md ——" in txt_a
    # возможно, для md-группы тоже fenced-блок без языка
    assert "```" in txt_a
    
    # Тестируем секцию 'web-api' из скоупа 'apps/web'
    manifest_web, plan_web, rendered_web = _process_section(monorepo, "web-api", "apps/web")
    
    # Секция web-api — чистый MD без fenced/FILE
    assert plan_web.md_only is True and plan_web.use_fence is False
    
    # Проверяем рендер секции web-api
    txt_web = rendered_web.text
    assert "# —— FILE:" not in txt_web
    assert "```" not in txt_web
    assert "# web docs" in txt_web  # содержимое apps/web/docs/index.md
    
    # Дополнительные проверки для CDM
    assert manifest_a.ref.scope_rel == "packages/svc-a"
    assert manifest_a.ref.name == "a"
    assert manifest_web.ref.scope_rel == "apps/web"
    assert manifest_web.ref.name == "web-api"
