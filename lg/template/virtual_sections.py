"""
Фабрика виртуальных секций для движка шаблонизации.

Создает временные секции для обработки Markdown-файлов через
плейсхолдеры ${md:...} с автоматической настройкой параметров адаптера.
"""

from __future__ import annotations

from pathlib import Path

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
        normalized_paths = self._normalize_file_paths(node.path, node.origin, node.is_glob)
        
        # Создаем конфигурацию фильтров
        filters = self._create_file_filter(normalized_paths, node.origin)
        
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

    def _normalize_file_paths(self, path: str, origin: str, is_glob: bool) -> list[str]:
        """
        Нормализует путь(и) к файлу(ам) для создания фильтра.
        
        Args:
            path: Исходный путь к файлу или паттерн глоба
            origin: Скоуп ("self" или путь к области, None для обычных md:)
            is_glob: True если path содержит символы глобов
            
        Returns:
            Список нормализованных путей для фильтра allow
        """
        # Обрабатываем глобы
        if is_glob:
            # Для глобов добавляем .md в конце если нет расширения
            if not path.endswith('.md') and not path.endswith('/*') and '.' not in Path(path).name:
                path = f"{path}.md"
            # Для глобов типа "docs/*" автоматически добавляем фильтр для .md файлов
            elif path.endswith('/*'):
                path = f"{path}.md"
        else:
            # Для обычных файлов добавляем расширение .md если не указано
            if not path.endswith('.md') and '.' not in Path(path).name:
                path = f"{path}.md"
        
        # Для ${md:file} без origin - ищем в корне текущей области
        if origin is None:
            if not path.startswith('/'):
                path = f"/{path}"
            return [path]
        
        # Для origin="self" путь считается относительно lg-cfg/
        if origin == "self":
            # Файлы ищутся в lg-cfg/ текущего скоупа
            if not path.startswith('/'):
                path = f"/lg-cfg/{path}"
            else:
                path = f"/lg-cfg{path}"
            return [path]
        
        # Для других скоупов (федеративные) путь относительно скоупа
        # НЕ относительно корня репозитория
        if path.startswith('lg-cfg/'):
            # Файл в lg-cfg другого скоупа - остается как есть
            return [f"/{path}"]
        else:
            # Обычный файл в корне другого скоупа или подпапке
            if not path.startswith('/'):
                path = f"/{path}"
            return [path]
    
    def _create_file_filter(self, normalized_paths: list[str], origin: str) -> FilterNode:
        """
        Создает фильтр для включения указанных файлов.
        
        Args:
            normalized_paths: Список нормализованных путей к файлам
            origin: Скоуп файла
            
        Returns:
            FilterNode с режимом allow для указанных файлов
        """
        return FilterNode(
            mode="allow",
            allow=normalized_paths,
            block=[]
        )
    
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
            
            # Создаем правило для включения секции по названию
            section_rule = SectionRule(
                match=SectionMatch(
                    kind="text",
                    pattern=node.anchor
                ),
                reason=f"md placeholder anchor: #{node.anchor}"
            )
            
            config.keep = MarkdownKeepCfg(
                sections=[section_rule],
                frontmatter=False  # По умолчанию не включаем frontmatter для якорных вставок
            )
        
        return config


__all__ = ["VirtualSectionFactory"]