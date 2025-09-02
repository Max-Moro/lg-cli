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
ImportPolicy = Literal["keep_all", "external_only", "summarize_long"]
LiteralPolicy = Literal["keep_all", "truncate", "collapse"]
PlaceholderStyle = Literal["auto", "inline", "block", "none"]


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
    policy: CommentPolicy = "keep_doc"
    max_length: Optional[int] = None  # максимальная длина сохраняемого комментария
    keep_annotations: List[str] = field(default_factory=list)  # regex аннотаций для сохранения
    strip_patterns: List[str] = field(default_factory=list)  # regex паттернов для удаления


@dataclass
class ImportConfig:
    """Конфигурация обработки импортов."""
    policy: ImportPolicy = "keep_all"
    max_items_before_summary: int = 10  # количество импортов, после которого включается суммаризация
    external_only_patterns: List[str] = field(default_factory=list)  # regex для определения внешних пакетов


@dataclass
class LiteralConfig:
    """Конфигурация обработки литералов данных."""
    max_string_length: int = 200
    max_array_elements: int = 20
    max_object_properties: int = 15
    max_literal_lines: int = 10
    collapse_threshold: int = 100  # байт, после которых включается collapse


@dataclass
class FieldConfig:
    """Конфигурация обработки полей/свойств."""
    keep_initializers: bool = True
    max_initializer_length: int = 50
    strip_trivial_accessors: bool = False  # геттеры/сеттеры в Java/C#


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
    mode: Literal["summary", "none"] = "summary"
    style: PlaceholderStyle = "auto"
    template: str = "/* … {kind} {name} (−{lines}) */"
    body_template: str = "/* … body omitted (−{lines}) */"
    import_template: str = "/* … {count} imports omitted */"
    literal_template: str = "/* … data omitted ({bytes} bytes) */"


@dataclass
class CodeCfg:
    """
    Базовая конфигурация для всех языковых адаптеров программирования.
    Наследуется язык-специфичными конфигурациями.
    """
    # Основные политики
    public_api_only: bool = False
    strip_function_bodies: Union[bool, FunctionBodyConfig] = False
    comment_policy: Union[CommentPolicy, CommentConfig] = "keep_doc"
    
    # Дополнительные оптимизации
    import_config: ImportConfig = field(default_factory=ImportConfig)
    literal_config: LiteralConfig = field(default_factory=LiteralConfig)
    field_config: FieldConfig = field(default_factory=FieldConfig)
    
    # Система плейсхолдеров
    placeholders: PlaceholderConfig = field(default_factory=PlaceholderConfig)
    
    # Бюджетирование
    budget: Optional[BudgetConfig] = None
    
    # Язык-специфичные расширения (raw dict для гибкости)
    lang_specific: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(d: Optional[Dict[str, Any]]) -> "CodeCfg":
        """Загрузка конфигурации из словаря YAML."""
        if not d:
            return CodeCfg()
        
        # Парсинг основных полей
        cfg = CodeCfg()
        cfg.public_api_only = bool(d.get("public_api_only", False))
        
        # strip_function_bodies: bool | dict
        sfb = d.get("strip_function_bodies", False)
        if isinstance(sfb, bool):
            cfg.strip_function_bodies = sfb
        elif isinstance(sfb, dict):
            cfg.strip_function_bodies = FunctionBodyConfig(
                mode=sfb.get("mode", "none"),
                min_lines=int(sfb.get("min_lines", 5)),
                except_patterns=list(sfb.get("except_patterns", [])),
                keep_annotated=list(sfb.get("keep_annotated", []))
            )
        
        # comment_policy: str | dict
        cp = d.get("comment_policy", "keep_doc")
        if isinstance(cp, str):
            cfg.comment_policy = cp
        elif isinstance(cp, dict):
            cfg.comment_policy = CommentConfig(
                policy=cp.get("policy", "keep_doc"),
                max_length=cp.get("max_length"),
                keep_annotations=list(cp.get("keep_annotations", [])),
                strip_patterns=list(cp.get("strip_patterns", []))
            )
        
        # Вложенные конфиги
        if "import_config" in d:
            ic = d["import_config"]
            cfg.import_config = ImportConfig(
                policy=ic.get("policy", "keep_all"),
                max_items_before_summary=int(ic.get("max_items_before_summary", 10)),
                external_only_patterns=list(ic.get("external_only_patterns", []))
            )
        
        if "literal_config" in d:
            lc = d["literal_config"]
            cfg.literal_config = LiteralConfig(
                max_string_length=int(lc.get("max_string_length", 200)),
                max_array_elements=int(lc.get("max_array_elements", 20)),
                max_object_properties=int(lc.get("max_object_properties", 15)),
                max_literal_lines=int(lc.get("max_literal_lines", 10)),
                collapse_threshold=int(lc.get("collapse_threshold", 100))
            )
        
        if "field_config" in d:
            fc = d["field_config"]
            cfg.field_config = FieldConfig(
                keep_initializers=bool(fc.get("keep_initializers", True)),
                max_initializer_length=int(fc.get("max_initializer_length", 50)),
                strip_trivial_accessors=bool(fc.get("strip_trivial_accessors", False))
            )
        
        if "placeholders" in d:
            pc = d["placeholders"]
            cfg.placeholders = PlaceholderConfig(
                mode=pc.get("mode", "summary"),
                style=pc.get("style", "auto"),
                template=pc.get("template", "/* … {kind} {name} (−{lines}) */"),
                body_template=pc.get("body_template", "/* … body omitted (−{lines}) */"),
                import_template=pc.get("import_template", "/* … {count} imports omitted */"),
                literal_template=pc.get("literal_template", "/* … data omitted ({bytes} bytes) */")
            )
        
        if "budget" in d:
            bc = d["budget"]
            cfg.budget = BudgetConfig(
                max_tokens_per_file=bc.get("max_tokens_per_file"),
                priority_order=list(bc.get("priority_order", [
                    "imports", "types", "public_methods", "fields", "private_methods", "docs"
                ]))
            )
        
        # Язык-специфичные расширения
        excluded_keys = {
            "public_api_only", "strip_function_bodies", "comment_policy",
            "import_config", "literal_config", "field_config", "placeholders", "budget"
        }
        cfg.lang_specific = {k: v for k, v in d.items() if k not in excluded_keys}
        
        return cfg


# ---- Язык-специфичные конфигурации ----

@dataclass
class PythonCfg(CodeCfg):
    """Конфигурация для Python адаптера."""
    # Наследует все поля от CodeCfg
    # Дополнительные Python-специфичные настройки можно добавить через lang_specific
    
    def __post_init__(self):
        # Устанавливаем Python-специфичные дефолты
        if self.placeholders.template == "/* … {kind} {name} (−{lines}) */":
            self.placeholders.template = "# … {kind} {name} (−{lines})"
            self.placeholders.body_template = "# … body omitted (−{lines})"
            self.placeholders.import_template = "# … {count} imports omitted"
            self.placeholders.literal_template = "# … data omitted ({bytes} bytes)"


@dataclass
class TypeScriptCfg(CodeCfg):
    """Конфигурация для TypeScript/JavaScript адаптера."""
    
    def __post_init__(self):
        # TypeScript-специфичные дефолты
        if not hasattr(self, '_ts_defaults_applied'):
            self.public_api_only = True  # для TS часто нужен только exported API
            self._ts_defaults_applied = True


@dataclass
class JavaCfg(CodeCfg):
    """Конфигурация для Java адаптера."""
    
    def __post_init__(self):
        # Java-специфичные дефолты
        if not hasattr(self, '_java_defaults_applied'):
            self.public_api_only = True
            self.field_config.strip_trivial_accessors = True  # убираем геттеры/сеттеры
            self._java_defaults_applied = True


@dataclass
class CppCfg(CodeCfg):
    """Конфигурация для C/C++ адаптера."""
    
    def __post_init__(self):
        # C/C++-специфичные настройки
        if not hasattr(self, '_cpp_defaults_applied'):
            # В заголовках (.h/.hpp) обычно нужны только объявления
            self.lang_specific.setdefault("header_mode", "declarations_only")
            self.lang_specific.setdefault("macro_policy", "summarize_large")
            self._cpp_defaults_applied = True


@dataclass
class ScalaCfg(CodeCfg):
    """Конфигурация для Scala адаптера."""
    
    def __post_init__(self):
        # Scala-специфичные настройки
        if not hasattr(self, '_scala_defaults_applied'):
            self.lang_specific.setdefault("keep_given_using", True)
            self.lang_specific.setdefault("case_class_policy", "signature_only")
            self._scala_defaults_applied = True


# ---- Реестр язык-специфичных конфигураций ----

LANG_CONFIG_CLASSES = {
    "python": PythonCfg,
    "typescript": TypeScriptCfg,
    "javascript": TypeScriptCfg,  # JS использует ту же конфигурацию что и TS
    "java": JavaCfg,
    "cpp": CppCfg,
    "c": CppCfg,  # C использует ту же конфигурацию что и C++
    "scala": ScalaCfg,
}


def create_lang_config(lang_name: str, raw_dict: Optional[Dict[str, Any]] = None) -> CodeCfg:
    """
    Фабрика для создания язык-специфичной конфигурации.
    
    Args:
        lang_name: имя языка адаптера
        raw_dict: сырые данные конфигурации из YAML
    
    Returns:
        Экземпляр соответствующей конфигурации
    """
    config_class = LANG_CONFIG_CLASSES.get(lang_name, CodeCfg)
    
    # Загружаем базовую конфигурацию
    base_cfg = CodeCfg.from_dict(raw_dict)
    
    # Если есть специализированный класс, создаем экземпляр с теми же данными
    if config_class != CodeCfg:
        # Копируем все поля из базовой конфигурации
        specialized_cfg = config_class()
        for field_name, field_value in base_cfg.__dict__.items():
            setattr(specialized_cfg, field_name, field_value)
        return specialized_cfg
    
    return base_cfg
