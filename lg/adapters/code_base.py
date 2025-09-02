"""
Базовый класс для адаптеров языков программирования.
Предоставляет общую функциональность для обработки кода.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from .base import BaseAdapter
from .code_model import CodeCfg, PlaceholderConfig, create_lang_config


class CodeAdapter(BaseAdapter[CodeCfg], ABC):
    """
    Базовый класс для всех адаптеров языков программирования.
    Предоставляет общие методы для обработки кода и системы плейсхолдеров.
    """

    @classmethod
    def load_cfg(cls, raw_cfg: dict | None) -> CodeCfg:
        """
        Загружает конфигурацию с учетом специфики языка.
        Переопределяет базовый метод для создания язык-специфичной конфигурации.
        """
        return create_lang_config(cls.name, raw_cfg)

    def should_skip(self, path: Path, text: str) -> bool:
        """
        Базовая логика пропуска файлов.
        Наследники могут переопределить для язык-специфичных эвристик.
        """
        return False

    def process(self, text: str, group_size: int, mixed: bool) -> Tuple[str, Dict[str, Any]]:
        """
        Основной метод обработки кода.
        Применяет все конфигурированные оптимизации.
        """
        meta = self._init_meta()
        
        # Парсим исходный код в промежуточное представление
        parsed = self.parse_code(text)
        
        # Применяем оптимизации согласно конфигурации
        optimized = self.apply_optimizations(parsed, meta)
        
        # Генерируем финальный текст с плейсхолдерами
        result_text = self.generate_output(optimized, meta)
        
        # Добавляем метаданные группы
        meta.update({
            "_group_size": group_size,
            "_group_mixed": mixed,
            "_adapter": self.name,
        })
        
        return result_text, meta

    def _init_meta(self) -> Dict[str, Any]:
        """Инициализирует метаданные для отслеживания изменений."""
        return {
            "code.removed.functions": 0,
            "code.removed.methods": 0,
            "code.removed.comments": 0,
            "code.removed.imports": 0,
            "code.removed.literals": 0,
            "code.trimmed.fields": 0,
            "code.placeholders": 0,
            "code.lines_saved": 0,
            "code.bytes_saved": 0,
        }

    @abstractmethod
    def parse_code(self, text: str) -> "CodeDocument":
        """
        Парсит исходный код в промежуточное представление.
        Должен быть реализован каждым язык-специфичным адаптером.
        """
        pass

    def apply_optimizations(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """
        Применяет все конфигурированные оптимизации к распарсенному коду.
        """
        if self.cfg.public_api_only:
            parsed = self.filter_public_api(parsed, meta)
        
        if self.cfg.strip_function_bodies:
            parsed = self.strip_function_bodies(parsed, meta)
        
        parsed = self.process_comments(parsed, meta)
        parsed = self.process_imports(parsed, meta)
        parsed = self.process_literals(parsed, meta)
        parsed = self.process_fields(parsed, meta)
        
        if self.cfg.budget:
            parsed = self.apply_budget(parsed, meta)
        
        return parsed

    def generate_output(self, optimized: "CodeDocument", meta: Dict[str, Any]) -> str:
        """
        Генерирует финальный текст из оптимизированного представления.
        Вставляет плейсхолдеры для удаленных частей.
        """
        return optimized.to_text(self.cfg.placeholders, meta)

    # ---- Методы оптимизации (базовые реализации) ----
    
    def filter_public_api(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Фильтрует только публичный API."""
        # Базовая реализация - наследники должны переопределить
        return parsed

    def strip_function_bodies(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Удаляет тела функций согласно конфигурации."""
        cfg = self.cfg.strip_function_bodies
        if not cfg:
            return parsed
        
        # Логика удаления тел функций
        # Наследники должны реализовать специфичную логику
        return parsed

    def process_comments(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает комментарии согласно политике."""
        policy = self.cfg.comment_policy
        if isinstance(policy, str) and policy == "keep_all":
            return parsed
        
        # Базовая логика обработки комментариев
        return parsed

    def process_imports(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает импорты согласно конфигурации."""
        cfg = self.cfg.import_config
        if cfg.policy == "keep_all":
            return parsed
        
        # Логика обработки импортов
        return parsed

    def process_literals(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает литералы данных."""
        cfg = self.cfg.literal_config
        # Логика усечения/схлопывания литералов
        return parsed

    def process_fields(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Обрабатывает поля/свойства."""
        cfg = self.cfg.field_config
        # Логика обработки полей
        return parsed

    def apply_budget(self, parsed: "CodeDocument", meta: Dict[str, Any]) -> "CodeDocument":
        """Применяет бюджетное ограничение токенов."""
        budget_cfg = self.cfg.budget
        if not budget_cfg or not budget_cfg.max_tokens_per_file:
            return parsed
        
        # Логика бюджетирования
        return parsed

    # ---- Утилиты для плейсхолдеров ----
    
    def create_placeholder(
        self,
        kind: str,
        name: str = "",
        lines_removed: int = 0,
        bytes_removed: int = 0,
        template_override: Optional[str] = None
    ) -> str:
        """
        Создает плейсхолдер для удаленного кода.
        
        Args:
            kind: тип удаленного элемента (function, method, class, import, etc.)
            name: имя элемента
            lines_removed: количество удаленных строк
            bytes_removed: количество удаленных байт
            template_override: переопределение шаблона
        """
        if self.cfg.placeholders.mode == "none":
            return ""
        
        template = template_override or self.cfg.placeholders.template
        
        # Подстановка переменных
        placeholder = template.format(
            kind=kind,
            name=name,
            lines=lines_removed,
            bytes=bytes_removed,
        )
        
        return placeholder

    def get_comment_style(self) -> Tuple[str, str]:
        """
        Возвращает стиль комментариев для языка (однострочный, многострочный).
        Должен быть переопределен наследниками.
        """
        return "//", ("/*", "*/")


# ---- Промежуточное представление кода ----

class CodeElement(ABC):
    """Базовый класс для элементов кода."""
    
    def __init__(self, start_line: int, end_line: int, text: str):
        self.start_line = start_line
        self.end_line = end_line
        self.original_text = text
        self.removed = False
        self.placeholder: Optional[str] = None

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1

    @property
    def byte_count(self) -> int:
        return len(self.original_text.encode('utf-8'))


class ImportElement(CodeElement):
    """Элемент импорта."""
    
    def __init__(self, start_line: int, end_line: int, text: str, 
                 module_name: str, is_external: bool = False):
        super().__init__(start_line, end_line, text)
        self.module_name = module_name
        self.is_external = is_external


class FunctionElement(CodeElement):
    """Элемент функции/метода."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 name: str, is_public: bool = True, signature: str = ""):
        super().__init__(start_line, end_line, text)
        self.name = name
        self.is_public = is_public
        self.signature = signature
        self.body_removed = False


class ClassElement(CodeElement):
    """Элемент класса/структуры."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 name: str, is_public: bool = True):
        super().__init__(start_line, end_line, text)
        self.name = name
        self.is_public = is_public
        self.methods: List[FunctionElement] = []
        self.fields: List[CodeElement] = []


class CommentElement(CodeElement):
    """Элемент комментария."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 is_doc: bool = False):
        super().__init__(start_line, end_line, text)
        self.is_doc = is_doc


class LiteralElement(CodeElement):
    """Элемент литерала данных."""
    
    def __init__(self, start_line: int, end_line: int, text: str,
                 literal_type: str = "unknown"):
        super().__init__(start_line, end_line, text)
        self.literal_type = literal_type  # string, array, object, etc.


class CodeDocument:
    """
    Промежуточное представление документа с кодом.
    Содержит разобранные элементы кода для обработки.
    """
    
    def __init__(self, original_lines: List[str]):
        self.original_lines = original_lines
        self.imports: List[ImportElement] = []
        self.functions: List[FunctionElement] = []
        self.classes: List[ClassElement] = []
        self.comments: List[CommentElement] = []
        self.literals: List[LiteralElement] = []
        self.other_elements: List[CodeElement] = []

    def to_text(self, placeholder_cfg: PlaceholderConfig, meta: Dict[str, Any]) -> str:
        """
        Генерирует финальный текст с учетом удаленных элементов и плейсхолдеров.
        """
        if placeholder_cfg.mode == "none":
            # Простое удаление без плейсхолдеров
            return self._generate_simple_output()
        
        return self._generate_output_with_placeholders(placeholder_cfg, meta)

    def _generate_simple_output(self) -> str:
        """Генерирует вывод без плейсхолдеров."""
        # Собираем все элементы, которые не помечены как удаленные
        result_lines = []
        for line in self.original_lines:
            # Упрощенная логика - в реальной реализации нужна более сложная обработка
            result_lines.append(line)
        
        return "\n".join(result_lines)

    def _generate_output_with_placeholders(
        self, 
        placeholder_cfg: PlaceholderConfig, 
        meta: Dict[str, Any]
    ) -> str:
        """Генерирует вывод с плейсхолдерами."""
        # Более сложная логика с учетом плейсхолдеров
        # В реальной реализации нужно пройти по всем элементам,
        # заменить удаленные на плейсхолдеры
        result_lines = []
        placeholders_count = 0
        
        for line in self.original_lines:
            # Упрощенная логика - реальная реализация будет зависеть от языка
            result_lines.append(line)
        
        meta["code.placeholders"] = placeholders_count
        return "\n".join(result_lines)
