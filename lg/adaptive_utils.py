"""
Утилиты для работы с режимами и тегами в адаптивной системе.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Set

from .config.modes import load_modes
from .config.tags import get_all_available_tags


def compute_active_tags(
    root: Path, 
    adaptive_modes: Dict[str, str], 
    extra_tags: Set[str]
) -> Set[str]:
    """
    Вычисляет множество активных тегов на основе режимов и дополнительных тегов.
    
    Args:
        root: Корень репозитория
        adaptive_modes: Словарь активных режимов {modeset_name: mode_name}
        extra_tags: Дополнительные теги, указанные явно
        
    Returns:
        Множество всех активных тегов
    """
    active_tags = set(extra_tags)  # Начинаем с явно указанных тегов
    
    # Загружаем конфигурацию режимов
    modes_config = load_modes(root)
    
    # Собираем теги из активных режимов
    for modeset_name, mode_name in adaptive_modes.items():
        modeset = modes_config.mode_sets.get(modeset_name)
        if not modeset:
            # Неизвестный набор режимов - пропускаем
            continue
        
        mode = modeset.modes.get(mode_name)
        if not mode:
            # Неизвестный режим - пропускаем
            continue
        
        # Добавляем теги режима
        active_tags.update(mode.tags)
    
    return active_tags


def validate_modes(root: Path, adaptive_modes: Dict[str, str]) -> None:
    """
    Проверяет корректность указанных режимов.
    Бросает исключение, если режим или набор режимов не найден.
    
    Args:
        root: Корень репозитория
        adaptive_modes: Словарь режимов для проверки
        
    Raises:
        ValueError: Если режим или набор режимов не найден
    """
    modes_config = load_modes(root)
    
    for modeset_name, mode_name in adaptive_modes.items():
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


def validate_tags(root: Path, tags: Set[str]) -> None:
    """
    Проверяет корректность указанных тегов.
    Выводит предупреждения для неизвестных тегов.
    
    Args:
        root: Корень репозитория  
        tags: Множество тегов для проверки
    """
    if not tags:
        return
    
    tag_sets, global_tags = get_all_available_tags(root)
    
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