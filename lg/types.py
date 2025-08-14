from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict


@dataclass(frozen=True)
class ProcessedResult:
    """
    Результат обработки одного файла адаптером (с учётом кэша).
    Возвращается из `_process_with_cache`.
    """
    processed_text: str
    meta: Dict
    key_hash: str
    key_path: Path


@dataclass(frozen=True)
class ProcessedBlob:
    """
    Единица данных для последующего подсчёта статистики:
    «сырой файл + обработанный текст + метаданные + ключи кэша».
    """
    abs_path: Path          # абсолютный путь к файлу на диске
    rel_path: str           # относительный путь (POSIX) от корня проекта
    size_bytes: int         # размер сырых байт файла
    processed_text: str     # результат adapter.process_ex / кэша
    meta: Dict              # метаданные адаптера
    raw_text: str           # исходный текст файла (для raw-подсчёта токенов)
    key_hash: str           # хэш ключа кэша processed
    key_path: Path          # путь к записи в кэше
