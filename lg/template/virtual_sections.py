"""
Фабрика виртуальных секций для движка шаблонизации.

Создает временные секции для обработки Markdown-файлов через
плейсхолдеры ${md:...} с автоматической настройкой параметров адаптера.
"""

from __future__ import annotations

import random
import time
from pathlib import Path
from typing import Dict, Any, Optional

from ..config.model import SectionCfg, AdapterConfig
from ..io.model import FilterNode  
from ..types import SectionRef


class VirtualSectionFactory:
    """
    Фабрика для создания виртуальных секций из Markdown-файлов.
    
    Генерирует уникальные секции для обработки отдельных документов
    с автоматической настройкой адаптеров на основе параметров плейсхолдера.
    """
    
    def __init__(self):
        """Инициализирует фабрику."""
        pass
    
    def create_for_markdown_file(
        self, 
        path: str, 
        origin: str = "self",
        heading_level: Optional[int] = None,
        strip_h1: Optional[bool] = None,
        repo_root: Optional[Path] = None
    ) -> tuple[str, SectionCfg, SectionRef]:
        """
        Создает виртуальную секцию для Markdown-файла.
        
        Args:
            path: Путь к файлу (относительно скоупа или абсолютный)
            origin: Скоуп файла ("self" или путь к области)
            heading_level: Желаемый максимальный уровень заголовков
            strip_h1: Флаг удаления H1 заголовка
            repo_root: Корень репозитория для резолвинга путей
            
        Returns:
            Кортеж (section_id, section_config, section_ref)
            
        Raises:
            ValueError: При некорректных параметрах
        """
        # Генерируем уникальный ID секции
        section_id = self._generate_unique_id()
        
        # Нормализуем путь к файлу
        normalized_path = self._normalize_file_path(path, origin)
        
        # Создаем конфигурацию фильтров
        filters = self._create_file_filter(normalized_path, origin)
        
        # Создаем конфигурацию Markdown-адаптера
        markdown_config = self._create_markdown_config(heading_level, strip_h1)
        
        # Создаем адаптеры
        adapters = {}
        if markdown_config:
            adapters["markdown"] = AdapterConfig.from_dict(markdown_config)
        
        # Создаем полную конфигурацию секции
        section_config = SectionCfg(
            extensions=[".md"],
            filters=filters,
            skip_empty=True,
            code_fence=True,
            path_labels="relative",
            adapters=adapters
        )
        
        # Создаем SectionRef
        if repo_root:
            if origin == "self":
                scope_dir = repo_root.resolve()
                scope_rel = ""
            else:
                scope_dir = (repo_root / origin).resolve()
                scope_rel = origin
        else:
            # Для тестирования без реальных путей
            scope_dir = Path("/fake/root")
            scope_rel = origin if origin != "self" else ""
        
        section_ref = SectionRef(
            name=section_id,
            scope_rel=scope_rel,
            scope_dir=scope_dir
        )
        
        return section_id, section_config, section_ref
    
    def _generate_unique_id(self) -> str:
        """
        Генерирует уникальный ID для виртуальной секции.
        
        Returns:
            Строка вида "_virtual_<timestamp>_<random>"
        """
        timestamp = int(time.time() * 1000)
        rand_part = random.randint(1000, 9999)
        return f"_virtual_{timestamp}_{rand_part}"
    
    def _normalize_file_path(self, path: str, origin: str) -> str:
        """
        Нормализует путь к файлу для создания фильтра.
        
        Args:
            path: Исходный путь к файлу
            origin: Скоуп ("self" или путь к области)
            
        Returns:
            Нормализованный путь для фильтра allow
        """
        # Добавляем расширение .md если не указано
        if not path.endswith('.md') and '.' not in Path(path).name:
            path = f"{path}.md"
        
        # Для origin="self" путь считается относительно корня репо
        if origin == "self":
            if not path.startswith('/'):
                path = f"/{path}"
            return path
        
        # Для других скоупов путь может быть:
        # 1. Относительно lg-cfg (специальный случай @self:)
        # 2. Относительно корня области
        if path.startswith('lg-cfg/'):
            # Специальный случай для файлов в lg-cfg
            return f"/{origin}/{path}"
        else:
            # Обычный случай - файл в области
            if not path.startswith('/'):
                path = f"/{origin}/lg-cfg/{path}"
            else:
                path = f"/{origin}{path}"
            return path
    
    def _create_file_filter(self, normalized_path: str, origin: str) -> FilterNode:
        """
        Создает фильтр для включения только указанного файла.
        
        Args:
            normalized_path: Нормализованный путь к файлу
            origin: Скоуп файла
            
        Returns:
            FilterNode с режимом allow для конкретного файла
        """
        return FilterNode(
            mode="allow",
            allow=[normalized_path],
            block=[]
        )
    
    def _create_markdown_config(
        self, 
        heading_level: Optional[int], 
        strip_h1: Optional[bool]
    ) -> Optional[Dict[str, Any]]:
        """
        Создает конфигурацию Markdown-адаптера.
        
        Args:
            heading_level: Желаемый максимальный уровень заголовков
            strip_h1: Флаг удаления H1 заголовка
            
        Returns:
            Словарь конфигурации адаптера или None если параметры не заданы
        """
        config = {}
        
        if heading_level is not None:
            if not isinstance(heading_level, int) or heading_level < 1 or heading_level > 6:
                raise ValueError(f"heading_level must be integer between 1 and 6, got {heading_level}")
            config["max_heading_level"] = heading_level
        
        if strip_h1 is not None:
            if not isinstance(strip_h1, bool):
                raise ValueError(f"strip_h1 must be boolean, got {type(strip_h1)}")
            config["strip_single_h1"] = strip_h1
        
        return config if config else None


__all__ = ["VirtualSectionFactory"]