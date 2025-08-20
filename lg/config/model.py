from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Literal

from lg.io.model import FilterNode

SCHEMA_VERSION = 7

@dataclass
class TargetRule:
    """
    Адресные оверрайды конфигураций адаптеров для конкретных путей.
    Поле match поддерживает строку или список строк-глобов (относительно корня репо).
    Все остальные ключи в исходном YAML внутри правила трактуются как имена адаптеров.
    """
    match: List[str] = field(default_factory=list)
    # имя_адаптера -> сырой dict-конфиг (как в секции)
    adapter_cfgs: Dict[str, Dict] = field(default_factory=dict)

@dataclass
class SectionCfg:
    extensions: List[str] = field(default_factory=lambda: [".py"])
    filters: FilterNode = field(
        default_factory=lambda: FilterNode(mode="block")  # default-allow
    )
    skip_empty: bool = True                  # глобальное правило
    code_fence: bool = True                  # оборачивать файлы в ```{lang}

    # Ленивые конфиги адаптеров: имя_адаптера → сырой dict из YAML
    adapters: Dict[str, dict] = field(default_factory=dict)

    # Адресные оверрайды по путям
    targets: List[TargetRule] = field(default_factory=list)

@dataclass
class Config:
    schema_version: int = SCHEMA_VERSION
    sections: Dict[str, SectionCfg] = field(default_factory=dict)

EmptyPolicy = Literal["inherit", "include", "exclude"]
