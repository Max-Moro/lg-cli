"""
Модель конфигурации для языковых адаптеров программирования.
Унифицированная базовая конфигурация + язык-специфичные расширения.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal, Union, Any

# ---- Типы для конфигурации ----

VisibilityLevel = Literal["public", "protected", "private", "internal", "exported"]
FunctionBodyStrip = Literal["none", "all", "public_only", "non_public", "large_only"]
CommentPolicy = Literal["keep_all", "strip_all", "keep_doc", "keep_first_sentence"]
ImportPolicy = Literal["keep_all", "strip_all", "strip_external", "strip_local"]
PlaceholderStyle = Literal["inline", "block", "none"]


@dataclass
class FunctionBodyConfig:
    """Конфигурация удаления тел функций/методов."""
    mode: FunctionBodyStrip = "none"
    min_lines: int = 5  # минимальное количество строк для удаления при mode="large_only"
    except_patterns: List[str] = field(default_factory=list)  # regex имен функций-исключений
    keep_annotated: List[str] = field(default_factory=list)  # regex аннотаций для сохранения


@dataclass
class CommentConfig:
    """Конфигурация обработки комментариев и документации."""
    policy: CommentPolicy = "keep_all"
    max_tokens: Optional[int] = None  # максимальное количество токенов для сохраняемого комментария
    keep_annotations: List[str] = field(default_factory=list)  # regex аннотаций для сохранения
    strip_patterns: List[str] = field(default_factory=list)  # regex паттернов для удаления


@dataclass
class ImportConfig:
    """Конфигурация обработки импортов."""
    policy: ImportPolicy = "keep_all"
    summarize_long: bool = False  # включить суммаризацию длинных списков импортов
    max_items_before_summary: int = 10  # количество импортов, после которого включается суммаризация
    external_patterns: List[str] = field(default_factory=list)  # regex для определения внешних пакетов

@dataclass
class LiteralConfig:
    """Конфигурация обработки литералов."""
    max_tokens: Optional[int] = None  # максимальный допустимый размер контента литерала в токенах


@dataclass
class BudgetConfig:
    """Бюджетирование токенов на файл."""
    max_tokens_per_file: Optional[int] = None
    priority_order: List[str] = field(default_factory=lambda: [
        "imports", "types", "public_methods", "fields", "private_methods", "docs"
    ])


@dataclass
class PlaceholderConfig:
    """Конфигурация плейсхолдеров для удаленного кода."""
    style: PlaceholderStyle = "inline"
    # Порог экономии токенов: savings / placeholder >= min_savings_ratio
    min_savings_ratio: float = 2.0
    # Абсолютный порог экономии для стиля style=="none" (полное удаление).
    min_abs_savings_if_none: int = 5


@dataclass
class CodeCfg:
    """
    Базовая конфигурация для всех языковых адаптеров программирования.
    Наследуется язык-специфичными конфигурациями.
    """
    # Основные политики
    public_api_only: bool = False
    strip_function_bodies: Union[bool, FunctionBodyConfig] = False
    comment_policy: Union[CommentPolicy, CommentConfig] = "keep_all"
    
    # Дополнительные оптимизации
    imports: ImportConfig = field(default_factory=ImportConfig)
    literals: LiteralConfig = field(default_factory=LiteralConfig)

    # Система плейсхолдеров
    placeholders: PlaceholderConfig = field(default_factory=PlaceholderConfig)

    # Бюджетирование
    budget: Optional[BudgetConfig] = None

    def general_load(self, d: Optional[Dict[str, Any]]):
        """Загрузка универсальной части конфигурации из словаря YAML."""
        d = d or {}

        # Парсинг основных полей
        self.public_api_only = bool(d.get("public_api_only", False))

        # strip_function_bodies: bool | dict
        sfb = d.get("strip_function_bodies", False)
        if isinstance(sfb, bool):
            self.strip_function_bodies = sfb
        elif isinstance(sfb, dict):
            self.strip_function_bodies = FunctionBodyConfig(
                mode=sfb.get("mode", "none"),
                min_lines=int(sfb.get("min_lines", 5)),
                except_patterns=list(sfb.get("except_patterns", [])),
                keep_annotated=list(sfb.get("keep_annotated", []))
            )

        # comment_policy: str | dict
        cp = d.get("comment_policy", "keep_all")
        if isinstance(cp, str):
            # Assign as CommentPolicy literal
            self.comment_policy = cp  # type: ignore[assignment]
        elif isinstance(cp, dict):
            self.comment_policy = CommentConfig(
                policy=cp.get("policy", "keep_all"),
                max_tokens=cp.get("max_tokens"),
                keep_annotations=list(cp.get("keep_annotations", [])),
                strip_patterns=list(cp.get("strip_patterns", []))
            )

        # Вложенные конфиги
        if "imports" in d:
            ic = d["imports"]
            self.imports = ImportConfig(
                policy=ic.get("policy", "keep_all"),
                summarize_long=bool(ic.get("summarize_long", False)),
                max_items_before_summary=int(ic.get("max_items_before_summary", 10)),
                external_patterns=list(ic.get("external_only_patterns", []))
            )

        if "literals" in d:
            lc = d["literals"]
            self.literals = LiteralConfig(
                max_tokens=lc.get("max_tokens")
            )

        if "placeholders" in d:
            pc = d["placeholders"]
            self.placeholders = PlaceholderConfig(
                style=pc.get("style", "inline"),
                min_savings_ratio=float(pc.get("min_savings_ratio", 2.0)),
                min_abs_savings_if_none=int(pc.get("min_abs_savings_if_none", 5)),
            )

        if "budget" in d:
            bc = d["budget"]
            self.budget = BudgetConfig(
                max_tokens_per_file=bc.get("max_tokens_per_file"),
                priority_order=list(bc.get("priority_order", [])) # TODO проработка приоритетов бюджетирование токенов по умолчанию
            )
