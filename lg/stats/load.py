from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional
from ruamel.yaml import YAML

from .model import (
    ModelsConfig,
    ModelInfo,
    PlanInfo,
    ResolvedModel,
    make_id,
    make_label,
    _slugify_plan
)

_yaml = YAML(typ="safe")
_CFG_FILE = "lg-cfg/models.yaml"

# -------------------- ДЕФОЛТЫ (при отсутствии lg-cfg/models.yaml) --------------------
# Источники:
# • OpenAI: o3/o3-mini/o4-mini/4o/4.1 окна контекста (официальные доки).
# • ChatGPT планы по контексту (Free/Plus/Pro/Enterprise) — справка OpenAI.
# • Gemini Apps (Free / Pro / Ultra) — справка Google.
# • Claude (Pro 200K, Enterprise 500K для Sonnet 4) — справка Anthropic.

_DEFAULT_MODELS: Dict[str, ModelInfo] = {
    # OpenAI
    "o3":                 ModelInfo(alias="o3", provider="openai", ctx_limit=200_000, encoder="cl100k_base"),
    "o3-mini":            ModelInfo(alias="o3-mini", provider="openai", ctx_limit=200_000, encoder="cl100k_base"),
    "o4-mini":            ModelInfo(alias="o4-mini", provider="openai", ctx_limit=200_000, encoder="cl100k_base"),
    "gpt-4o":             ModelInfo(alias="gpt-4o", provider="openai", ctx_limit=128_000, encoder="o200k_base"),
    "gpt-4.1":            ModelInfo(alias="gpt-4.1", provider="openai", ctx_limit=1_000_000, encoder="o200k_base"),
    # Anthropic
    "claude-3.5-sonnet":  ModelInfo(alias="claude-3.5-sonnet", provider="anthropic", ctx_limit=200_000, encoder="cl100k_base"),
    # Google
    "gemini-1.5-pro":     ModelInfo(alias="gemini-1.5-pro", provider="google", ctx_limit=1_000_000, encoder="cl100k_base"),
    "gemini-2.5-pro":     ModelInfo(alias="gemini-2.5-pro", provider="google", ctx_limit=1_000_000, encoder="cl100k_base"),
    # Cohere (для полноты — по публичным источникам)
    "command-r-plus":     ModelInfo(alias="command-r-plus", provider="cohere", ctx_limit=128_000, encoder="cl100k_base"),
}

_DEFAULT_PLANS: List[PlanInfo] = [
    # OpenAI ChatGPT планы (контекст в чате)
    PlanInfo(name="Free",         provider="openai",   ctx_cap=16_000,  featured=False),
    PlanInfo(name="Plus/Team",    provider="openai",   ctx_cap=32_000,  featured=True),
    PlanInfo(name="Pro",          provider="openai",   ctx_cap=128_000, featured=True),
    # Gemini Apps (контекст в приложении)
    PlanInfo(name="Free",         provider="google",   ctx_cap=32_000,  featured=False),
    PlanInfo(name="Pro",          provider="google",   ctx_cap=1_000_000, featured=True),
    PlanInfo(name="Ultra",        provider="google",   ctx_cap=1_000_000, featured=True),
    # Claude (контекст в веб-клиенте Anthropic)
    PlanInfo(name="Free",         provider="anthropic", ctx_cap=32_000,  featured=False),
    PlanInfo(name="Pro",          provider="anthropic", ctx_cap=200_000, featured=True),
    PlanInfo(name="Enterprise",   provider="anthropic", ctx_cap=500_000, featured=True),
]

# -----------------------------------------------------------------------

def _cfg_path(root: Path) -> Path:
    return (root / _CFG_FILE).resolve()

def load_models(root: Path) -> ModelsConfig:
    p = _cfg_path(root)
    if not p.is_file():
        return ModelsConfig(schema_version=1, models=dict(_DEFAULT_MODELS), plans=list(_DEFAULT_PLANS))
    raw = _yaml.load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise RuntimeError("models.yaml must be a mapping with keys: schema_version?, models, plans?")
    schema_version = int(raw.get("schema_version", 1))
    models_node = raw.get("models", {}) or {}
    plans_node = raw.get("plans", []) or []
    models: Dict[str, ModelInfo] = {}
    for alias, node in models_node.items():
        if not isinstance(node, dict):
            raise RuntimeError(f"models.{alias}: must be a mapping")
        provider = str(node.get("provider", "openai"))
        ctx_limit = int(node.get("ctx_limit"))
        encoder = str(node.get("encoder", "cl100k_base"))
        models[str(alias)] = ModelInfo(alias=str(alias), provider=provider, ctx_limit=ctx_limit, encoder=encoder)
    plans: List[PlanInfo] = []
    for idx, node in enumerate(plans_node):
        if not isinstance(node, dict):
            raise RuntimeError(f"plans[{idx}]: must be a mapping")
        name = str(node.get("name"))
        provider = str(node.get("provider"))
        ctx_cap = int(node.get("ctx_cap"))
        featured = bool(node.get("featured", False))
        plans.append(PlanInfo(name=name, provider=provider, ctx_cap=ctx_cap, featured=featured))
    return ModelsConfig(schema_version=schema_version, models=models, plans=plans)

def list_models(root: Path) -> List[dict]:
    """
    Возвращаем массив объектов:
      {id, label, base, plan, provider, encoder, ctxLimit}
    """
    cfg = load_models(root)
    out: List[dict] = []
    for m in cfg.models.values():
        # голая модель
        out.append({
            "id": make_id(m.alias, None),
            "label": make_label(m.alias, None),
            "base": m.alias,
            "plan": None,
            "provider": m.provider,
            "encoder": m.encoder,
            "ctxLimit": m.ctx_limit,
        })
        # комбо с избранными планами
        for p in cfg.plans:
            if p.provider != m.provider or not p.featured:
                continue
            eff = min(m.ctx_limit, p.ctx_cap)
            out.append({
                "id": make_id(m.alias, p.name),
                "label": make_label(m.alias, p.name),
                "base": m.alias,
                "plan": p.name,
                "provider": m.provider,
                "encoder": m.encoder,
                "ctxLimit": eff,
            })
    # стабильная сортировка по id
    out.sort(key=lambda x: x["id"])
    return out

def get_model_info(root: Path, model_id: str) -> ResolvedModel:
    """
    Резолвит модель ТОЛЬКО по безопасному идентификатору:
      • "<base>"
      • "<base>__<plan-slug>"

    Где <plan-slug> — slug(Plan.name): lowercase, пробелы/подчёркивания → '-', только [a-z0-9-].
    """
    cfg = load_models(root)
    s = (model_id or "").strip()
    if not s:
        raise KeyError("Model id is empty")

    # Разбор id: допускаем максимум один '__'
    if "__" in s:
        parts = s.split("__")
        if len(parts) != 2:
            raise KeyError(f"Invalid model id format: '{model_id}'")
        base, slug = parts[0].strip(), parts[1].strip().lower()
    else:
        base, slug = s, None

    # Проверка базовой модели
    m = cfg.models.get(base)
    if not m:
        raise KeyError(f"Model '{base}' not found")

    # Если без плана — возвращаем «физическую» модель
    if not slug:
        return ResolvedModel(
            id=make_id(m.alias, None),
            base=m.alias,
            provider=m.provider,
            encoder=m.encoder,
            ctx_limit=int(m.ctx_limit),
            plan=None,
        )

    # Поиск плана по slug среди планов того же провайдера
    chosen: Optional[PlanInfo] = None
    for p in cfg.plans:
        if p.provider != m.provider:
            continue
        if _slugify_plan(p.name) == slug:
            chosen = p
            break
    if chosen is None:
        raise KeyError(f"Plan slug '{slug}' not found for provider '{m.provider}'")

    eff_limit = min(m.ctx_limit, chosen.ctx_cap)
    return ResolvedModel(
        id=make_id(m.alias, chosen.name),
        base=m.alias,
        provider=m.provider,
        encoder=m.encoder,
        ctx_limit=int(eff_limit),
        plan=chosen.name,
    )