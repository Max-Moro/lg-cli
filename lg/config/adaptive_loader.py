"""
Утилиты для работы с режимами и тегами в адаптивной системе.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set, Tuple, Optional

from .modes import load_modes, ModesConfig
from .tags import load_tags, TagsConfig, TagSet, Tag
from .adaptive_model import ModeOptions


class AdaptiveConfigLoader:
    """
    Централизованный загрузчик конфигурации режимов и тегов с кэшированием.
    Избегает повторной загрузки одних и тех же YAML-файлов.
    """
    
    def __init__(self, root: Path):
        self.root = root
        self._modes_config: Optional[ModesConfig] = None
        self._tags_config: Optional[TagsConfig] = None
    
    def get_modes_config(self) -> ModesConfig:
        """Загружает конфигурацию режимов с кэшированием."""
        if self._modes_config is None:
            self._modes_config = load_modes(self.root)
        return self._modes_config
    
    def get_tags_config(self) -> TagsConfig:
        """Загружает конфигурацию тегов с кэшированием."""
        if self._tags_config is None:
            self._tags_config = load_tags(self.root)
        return self._tags_config
    
    def get_all_available_tags(self) -> Tuple[Dict[str, TagSet], Dict[str, Tag]]:
        """Возвращает все доступные теги, разделенные на наборы и глобальные."""
        config = self.get_tags_config()
        return config.tag_sets, config.global_tags


def process_adaptive_options(
    root: Path,
    modes: Dict[str, str],
    extra_tags: Set[str]
) -> Tuple[Set[str], ModeOptions, AdaptiveConfigLoader]:
    """
    Основная функция для обработки адаптивных опций.
    Выполняет валидацию режимов и тегов, вычисляет активные теги и мержит опции режимов.
    
    Args:
        root: Корень репозитория
        modes: Словарь активных режимов {modeset_name: mode_name}
        extra_tags: Дополнительные теги, указанные явно
        
    Returns:
        Кортеж (активные_теги, смердженные_опции_режимов, загрузчик_конфигурации)
        
    Raises:
        ValueError: Если режим или набор режимов не найден
    """
    loader = AdaptiveConfigLoader(root)
    
    # Валидируем режимы
    if modes:
        _validate_modes_with_config(loader.get_modes_config(), modes)
    
    # Валидируем теги
    if extra_tags:
        _validate_tags_with_config(loader.get_all_available_tags(), extra_tags)
    
    # Вычисляем активные теги
    active_tags = _compute_active_tags_with_config(
        loader.get_modes_config(), 
        modes,
        extra_tags
    )
    
    # Мержим опции от всех активных режимов
    mode_options = ModeOptions.merge_from_modes(
        loader.get_modes_config(), 
        modes
    )
    
    return active_tags, mode_options, loader


def _validate_modes_with_config(modes_config: ModesConfig, modes: Dict[str, str]) -> None:
    """
    Проверяет корректность указанных режимов с использованием уже загруженной конфигурации.
    
    Args:
        modes_config: Загруженная конфигурация режимов
        modes: Словарь режимов для проверки
        
    Raises:
        ValueError: Если режим или набор режимов не найден
    """
    for modeset_name, mode_name in modes.items():
        modeset = modes_config.mode_sets.get(modeset_name)
        if not modeset:
            available_modesets = list(modes_config.mode_sets.keys())
            raise ValueError(
                f"Unknown mode set '{modeset_name}'. "
                f"Available mode sets: {', '.join(available_modesets)}"
            )
        
        if mode_name not in modeset.modes:
            available_modes = list(modeset.modes.keys())
            raise ValueError(
                f"Unknown mode '{mode_name}' in mode set '{modeset_name}'. "
                f"Available modes: {', '.join(available_modes)}"
            )


def _validate_tags_with_config(all_tags: Tuple[Dict[str, TagSet], Dict[str, Tag]], tags: Set[str]) -> None:
    """
    Проверяет корректность указанных тегов с использованием уже загруженной конфигурации.
    Выводит предупреждения для неизвестных тегов.
    
    Args:
        all_tags: Кортеж (наборы_тегов, глобальные_теги)
        tags: Множество тегов для проверки
    """
    if not tags:
        return
    
    tag_sets, global_tags = all_tags
    
    # Собираем все известные теги
    all_known_tags = set(global_tags.keys())
    for tag_set in tag_sets.values():
        all_known_tags.update(tag_set.tags.keys())
    
    # Проверяем на неизвестные теги
    unknown_tags = tags - all_known_tags
    if unknown_tags:
        import logging
        logging.warning(
            f"Unknown tags: {', '.join(sorted(unknown_tags))}. "
            f"They will be processed but may not affect the output."
        )


def _compute_active_tags_with_config(
    modes_config: ModesConfig, 
    modes: Dict[str, str],
    extra_tags: Set[str]
) -> Set[str]:
    """
    Вычисляет множество активных тегов с использованием уже загруженной конфигурации.
    
    Args:
        modes_config: Загруженная конфигурация режимов
        modes: Словарь активных режимов {modeset_name: mode_name}
        extra_tags: Дополнительные теги, указанные явно
        
    Returns:
        Множество всех активных тегов
    """
    active_tags = set(extra_tags)  # Начинаем с явно указанных тегов
    
    # Собираем теги из активных режимов
    for modeset_name, mode_name in modes.items():
        modeset = modes_config.mode_sets.get(modeset_name)
        if not modeset:
            # Неизвестный набор режимов - пропускаем (уже проверено в валидации)
            continue
        
        mode = modeset.modes.get(mode_name)
        if not mode:
            # Неизвестный режим - пропускаем (уже проверено в валидации)
            continue
        
        # Добавляем теги режима
        active_tags.update(mode.tags)
    
    return active_tags
