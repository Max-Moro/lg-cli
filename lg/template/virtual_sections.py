"""
Фабрика виртуальных секций для движка шаблонизации.

Создает временные секции для обработки Markdown-файлов через
плейсхолдеры ${md:...} с автоматической настройкой параметров адаптера.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .heading_context import HeadingContext
from .nodes import MarkdownFileNode
from ..config.model import SectionCfg, AdapterConfig
from ..io.model import FilterNode
from ..markdown import MarkdownCfg
from ..types import SectionRef


class VirtualSectionFactory:
    """
    Фабрика для создания виртуальных секций из Markdown-файлов.
    
    Генерирует уникальные секции для обработки отдельных документов
    с автоматической настройкой адаптеров на основе параметров плейсхолдера.
    """
    
    def __init__(self):
        """Инициализирует фабрику."""
        self._counter = 0

    def create_for_markdown_file(
        self, 
        node: MarkdownFileNode,
        repo_root: Path,
        heading_context: HeadingContext
    ) -> tuple[SectionCfg, SectionRef]:
        """
        Создает виртуальную секцию для Markdown-файла или набора файлов.
        
        Args:
            node: Узел MarkdownFileNode с полной информацией о включаемом файле
            repo_root: Корень репозитория для резолвинга путей
            heading_context: Контекст заголовков
            
        Returns:
            Кортеж (section_config, section_ref)
            
        Raises:
            ValueError: При некорректных параметрах
        """
        # Нормализуем путь к файлу(ам)
        normalized_path = self._normalize_file_path(node.path, node.origin, node.is_glob)
        
        # Создаем конфигурацию фильтров
        filters = self._create_file_filter(normalized_path)

        # Создаем конфигурацию Markdown-адаптера
        markdown_config_raw = self._create_markdown_config(node, heading_context).to_dict()

        # Создаем полную конфигурацию секции
        section_config = SectionCfg(
            extensions=[".md"],
            filters=filters,
            code_fence=False,
            adapters={"markdown": AdapterConfig(base_options=markdown_config_raw)}
        )

        # Создаем SectionRef
        if node.origin is None or node.origin == "self":
            # Для md: или md@self: используем текущий скоуп
            scope_dir = repo_root.resolve()
            scope_rel = ""
        else:
            # Для md@origin: используем указанный скоуп
            scope_dir = (repo_root / node.origin).resolve()
            scope_rel = node.origin

        section_ref = SectionRef(
            name=self._generate_name(),
            scope_rel=scope_rel,
            scope_dir=scope_dir
        )

        return section_config, section_ref

    def _generate_name(self) -> str:
        """
        Генерирует уникальное имя для виртуальной секции.

        Returns:
            Строка вида "_virtual_<counter>"
        """
        self._counter += 1
        return f"_virtual_{self._counter}"

    def _normalize_file_path(self, path: str, origin: Optional[str], is_glob: bool) -> str:
        """
        Нормализует путь к файлу для создания фильтра.

        Args:
            path: Исходный путь к файлу или паттерн глоба
            origin: Скоуп ("self" или путь к области, None для обычных md:)
            is_glob: True если path содержит символы глобов

        Returns:
            Нормализованный путь для фильтра allow
        """
        # Нормализуем путь
        normalized = path.strip()

        # Автоматически добавляем расширение .md, если оно отсутствует
        if not is_glob:
            # Для обычных файлов проверяем и добавляем .md
            if not normalized.endswith('.md') and not normalized.endswith('.markdown'):
                normalized += '.md'
        else:
            # Для глобов не добавляем расширение автоматически
            pass

        # Для разных типов origin формируем разные пути
        if origin is not None:
            # Для @origin: файлы ВСЕГДА ищутся в lg-cfg/ области скоупа origin
            if normalized.startswith('/'):
                return f"/lg-cfg{normalized}"
            else:
                return f"/lg-cfg/{normalized}"

        else:
            # Для обычных md: файлы ищутся относительно корня репы
            if normalized.startswith('/'):
                return normalized
            else:
                return f"/{normalized}"

    def _create_file_filter(self, path: str) -> FilterNode:
        """
        Создает фильтр для включения указанных файлов.

        Args:
            path: Нормализованный путь к файлу

        Returns:
            FilterNode с режимом allow для указанных файлов
        """
        return FilterNode(mode="allow", allow=[path])
    
    def _create_markdown_config(
        self, 
        node: MarkdownFileNode,
        heading_context: HeadingContext
    ) -> MarkdownCfg:
        """
        Создает конфигурацию Markdown-адаптера.
        
        Args:
            node: Узел MarkdownFileNode с полной информацией о включаемом файле
            heading_context: Контекст заголовков для определения параметров
            
        Returns:
            Типизированная конфигурация Markdown-адаптера
        """
        # Получаем эффективные значения с учетом приоритета: явные > контекстуальные
        effective_heading_level = node.heading_level if node.heading_level is not None else heading_context.heading_level
        effective_strip_h1 = node.strip_h1 if node.strip_h1 is not None else heading_context.strip_h1
        
        # Создаем базовую конфигурацию
        config = MarkdownCfg(
            max_heading_level=effective_heading_level,
            strip_single_h1=effective_strip_h1 if effective_strip_h1 is not None else False,
            placeholder_inside_heading=heading_context.placeholder_inside_heading
        )

        # Если есть якорь (anchor), создаем keep-конфигурацию для включения только нужной секции
        if node.anchor:
            from ..markdown.model import MarkdownKeepCfg, SectionRule, SectionMatch
            from ..markdown.slug import slugify_github
            
            # Создаем правило для включения секции по названию
            # Используем slug-сопоставление для более гибкого поиска
            # Нормализуем якорь перед созданием slug (добавляем пробелы в разумных местах)
            normalized_anchor = self._normalize_anchor_for_slug(node.anchor)
            anchor_slug = slugify_github(normalized_anchor)
            section_rule = SectionRule(
                match=SectionMatch(
                    kind="slug",
                    pattern=anchor_slug
                ),
                reason=f"md placeholder anchor: #{node.anchor} (slug: {anchor_slug})"
            )
            
            config.keep = MarkdownKeepCfg(
                sections=[section_rule],
                frontmatter=False  # По умолчанию не включаем frontmatter для якорных вставок
            )
        
        return config

    def _normalize_anchor_for_slug(self, anchor: str) -> str:
        """
        Нормализует якорь для создания согласованного slug.

        Добавляет пробелы после двоеточий и других разделителей,
        чтобы slug от якоря соответствовал slug от реального заголовка.

        Args:
            anchor: Исходный якорь из плейсхолдера

        Returns:
            Нормализованный якорь
        """
        import re

        # Добавляем пробел после двоеточия, если его нет
        # FAQ:Common Questions -> FAQ: Common Questions
        normalized = re.sub(r':(?!\s)', ': ', anchor)

        # Добавляем пробел после амперсанда, если его нет
        # API&Usage -> API & Usage
        normalized = re.sub(r'&(?!\s)', ' & ', normalized)

        # Убираем лишние пробелы
        normalized = re.sub(r'\s+', ' ', normalized).strip()

        return normalized


__all__ = ["VirtualSectionFactory"]