"""
Утилита для управления корневым .gitignore файлом.

Предоставляет централизованную логику добавления записей в .gitignore
для различных компонентов системы кеширования.
"""

from __future__ import annotations

from pathlib import Path
import logging

logger = logging.getLogger(__name__)

__all__ = ["ensure_gitignore_entry"]


def ensure_gitignore_entry(root: Path, entry: str, *, comment: str | None = None) -> bool:
    """
    Гарантирует наличие записи в корневом .gitignore файле.
    
    Args:
        root: Корень проекта (где находится .gitignore)
        entry: Запись для добавления (например, ".lg-cache/")
        comment: Опциональный комментарий перед записью
        
    Returns:
        True если запись была добавлена, False если уже существовала
        
    Note:
        - Создает .gitignore если его нет
        - Проверяет существующие записи (игнорирует комментарии и пустые строки)
        - Добавляет запись в конец файла с переводом строки
        - Все операции best-effort (не роняют программу при ошибках)
    """
    gitignore_path = root / ".gitignore"
    
    try:
        # Нормализуем запись (убираем лишние пробелы, обеспечиваем trailing slash для директорий)
        entry_normalized = entry.strip()
        if not entry_normalized:
            logger.warning("Empty gitignore entry requested, skipping")
            return False
        
        # Читаем существующий файл если есть
        existing_lines = []
        if gitignore_path.exists():
            try:
                content = gitignore_path.read_text(encoding="utf-8")
                existing_lines = content.splitlines()
            except Exception as e:
                logger.warning(f"Failed to read .gitignore: {e}")
                # Продолжаем работу с пустым списком
        
        # Проверяем наличие записи (игнорируем комментарии и пустые строки)
        for line in existing_lines:
            line_stripped = line.strip()
            if line_stripped and not line_stripped.startswith("#"):
                if line_stripped == entry_normalized:
                    # Запись уже существует
                    return False
        
        # Формируем новую запись с опциональным комментарием
        new_content_parts = []
        
        # Сохраняем существующее содержимое
        if existing_lines:
            new_content_parts.append("\n".join(existing_lines))
            # Добавляем пустую строку перед нашей записью если файл не пустой
            # и последняя строка не пустая
            if existing_lines[-1].strip():
                new_content_parts.append("")
        
        # Добавляем комментарий если указан
        if comment:
            new_content_parts.append(f"# {comment}")
        
        # Добавляем саму запись
        new_content_parts.append(entry_normalized)
        
        # Записываем обновленный .gitignore
        final_content = "\n".join(new_content_parts)
        if not final_content.endswith("\n"):
            final_content += "\n"
        
        gitignore_path.write_text(final_content, encoding="utf-8")
        
        logger.info(f"Added '{entry_normalized}' to .gitignore")
        return True
        
    except Exception as e:
        # Best-effort: логируем ошибку но не роняем программу
        logger.warning(f"Failed to update .gitignore: {e}")
        return False
