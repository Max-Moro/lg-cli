"""
AST узлы для Markdown-плейсхолдеров.

Адаптированы из lg.template.nodes для модульной архитектуры v2.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ..nodes import TemplateNode


@dataclass(frozen=True)
class MarkdownFileNode(TemplateNode):
    """
    Плейсхолдер для прямого включения Markdown-файла ${md:path} или ${md:path#section}.
    
    Представляет ссылку на Markdown-файл (или набор файлов через глобы),
    который должен быть обработан и включен в текущее место.
    
    Attributes:
        path: Путь к файлу относительно скоупа (например, "docs/api" или "*.md")
        origin: Скоуп для адресных ссылок ("self", путь к lg-cfg или None)
        
        # Параметры обработки заголовков
        heading_level: Явно заданный уровень заголовков (если None - автоопределение)
        strip_h1: Флаг удаления H1 (если None - автоопределение)
        
        # Частичное включение
        anchor: Якорь для включения только определенной секции
        
        # Условное включение
        condition: Текст условия для проверки тегов/режимов
        
        # Поддержка глобов
        is_glob: Флаг того, что path содержит глоб-паттерн
    """
    path: str                      # Путь к файлу (может содержать глобы)
    origin: Optional[str] = None   # "self" или путь к скоупу
    
    # Параметры обработки заголовков (автоматические или явные)
    heading_level: Optional[int] = None    # Явный уровень заголовков
    strip_h1: Optional[bool] = None        # Флаг удаления H1
    
    # Частичное включение
    anchor: Optional[str] = None           # Якорь для включения секции
    
    # Условное включение
    condition: Optional[str] = None        # Условие для проверки
    
    # Поддержка глобов
    is_glob: bool = False                  # Флаг глоб-паттерна

    def canon_key(self) -> str:
        """
        Возвращает канонический ключ для кэширования и дедупликации.
        
        Returns:
            Строка вида "md:path" или "md@origin:path" с параметрами
        """
        parts = ["md"]
        
        # Добавляем origin если указан
        if self.origin and self.origin != "self":
            parts.append(f"@{self.origin}")
        
        parts.append(f":{self.path}")
        
        # Добавляем якорь если указан
        if self.anchor:
            parts.append(f"#{self.anchor}")
        
        # Добавляем параметры если указаны
        params = []
        if self.heading_level is not None:
            params.append(f"level:{self.heading_level}")
        if self.strip_h1 is not None:
            params.append(f"strip_h1:{str(self.strip_h1).lower()}")
        if self.condition:
            params.append(f"if:{self.condition}")
        
        if params:
            parts.append("," + ",".join(params))
        
        return "".join(parts)


__all__ = ["MarkdownFileNode"]
