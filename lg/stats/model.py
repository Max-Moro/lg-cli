from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ModelInfo:
    alias: str         # напр. "o3"
    provider: str      # "openai" | "anthropic" | "google" | "cohere" | ...
    ctx_limit: int     # «физическое» окно модели (токены)
    encoder: str       # имя энкодера для tiktoken

@dataclass(frozen=True)
class PlanInfo:
    name: str          # напр. "Pro", "Plus/Team"
    provider: str      # к какому провайдеру относится план
    ctx_cap: int       # маркетинговый колпак на окно контекста
    featured: bool = False  # показывать в UI-комбинациях

@dataclass
class ModelsConfig:
    models: Dict[str, ModelInfo] = field(default_factory=dict)
    plans: List[PlanInfo] = field(default_factory=list)

    def list_display_names(self) -> List[str]:
        out: List[str] = []
        for m in self.models.values():
            out.append(m.alias)
            for p in self.plans:
                if p.provider == m.provider and p.featured:
                    out.append(f"{m.alias} ({p.name})")
        # стабильная сортировка без дубликатов
        return sorted(dict.fromkeys(out).keys())

@dataclass(frozen=True)
class ResolvedModel:
    # Полностью резолвленное представление (с учётом плана)
    id: str
    label: str
    base: str          # базовый alias модели без плана
    provider: str
    encoder: str
    ctx_limit: int     # эффективный лимит = min(model.ctx_limit, plan.ctx_cap?) либо «физический»
    plan: Optional[str] = None

_slug_re = re.compile(r"[^a-z0-9-]+")

def _slugify_plan(name: str) -> str:
    s = name.strip().lower().replace(" ", "-").replace("_", "-")
    s = _slug_re.sub("", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s

def make_id(base: str, plan: Optional[str]) -> str:
    if not plan:
        return base
    return f"{base}__{_slugify_plan(plan)}"
