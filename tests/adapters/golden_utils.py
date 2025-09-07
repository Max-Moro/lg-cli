"""
Утилиты для golden-тестов языковых адаптеров.
Предоставляет унифицированную работу с эталонными файлами.
"""

import os
from pathlib import Path
from typing import Optional

import pytest


def assert_golden_match(
    result: str, 
    golden_name: str, 
    language: Optional[str] = None,
    update_golden: Optional[bool] = None
) -> None:
    """
    Универсальная функция для сравнения результатов с golden-файлами.
    
    Args:
        result: Фактический результат для сравнения
        golden_name: Имя golden-файла (без расширения .golden)
        language: Язык адаптера ("python", "typescript", etc.). 
                 Если не указан, определяется автоматически из контекста теста
        update_golden: Флаг обновления golden-файла. 
                      Если None, берется из переменной окружения PYTEST_UPDATE_GOLDENS
    
    Raises:
        AssertionError: Если результат не совпадает с эталоном
    """
    # Определяем язык автоматически, если не указан
    if language is None:
        language = _detect_language_from_test_context()
    
    # Определяем флаг обновления
    if update_golden is None:
        update_golden = os.getenv("PYTEST_UPDATE_GOLDENS") == "1"
    
    # Формируем путь к golden-файлу
    golden_file = _get_golden_file_path(language, golden_name)
    
    # Нормализуем результат для стабильности
    normalized_result = _normalize_result(result)
    
    # Логика сравнения/обновления
    if update_golden or not golden_file.exists():
        golden_file.parent.mkdir(parents=True, exist_ok=True)
        golden_file.write_text(normalized_result, encoding='utf-8')
        if update_golden:
            pytest.skip(f"Updated golden file: {golden_file}")
    
    expected = golden_file.read_text(encoding='utf-8')
    if normalized_result != expected:
        # Создаем информативное сообщение об ошибке
        diff_msg = _create_diff_message(expected, normalized_result, golden_file)
        raise AssertionError(diff_msg)


def _detect_language_from_test_context() -> str:
    """
    Определяет язык адаптера из контекста текущего теста.
    Анализирует путь к тестовому файлу.
    """
    import inspect
    
    # Получаем стек вызовов и ищем файл теста
    for frame_info in inspect.stack():
        frame_path = Path(frame_info.filename)
        
        # Ищем паттерн tests/adapters/<language>/test_*.py
        if (frame_path.name.startswith("test_") and 
            frame_path.suffix == ".py" and
            "adapters" in frame_path.parts):
            
            parts = frame_path.parts
            try:
                adapters_idx = parts.index("adapters")
                if adapters_idx + 1 < len(parts):
                    language = parts[adapters_idx + 1]
                    # Проверяем что это действительно язык (не __pycache__ и т.д.)
                    if language not in ("__pycache__", "__init__.py") and not language.startswith("."):
                        return language
            except ValueError:
                continue
    
    # Fallback: пытаемся извлечь из имени модуля теста
    test_module = inspect.getmodule(inspect.stack()[2].frame)
    if test_module and test_module.__name__:
        module_parts = test_module.__name__.split('.')
        for i, part in enumerate(module_parts):
            if part == "adapters" and i + 1 < len(module_parts):
                return module_parts[i + 1]
    
    raise ValueError(
        "Cannot auto-detect language for golden test. "
        "Please specify language parameter explicitly, or ensure test is in "
        "tests/adapters/<language>/ directory structure."
    )


def _get_golden_file_path(language: str, golden_name: str) -> Path:
    """
    Формирует путь к golden-файлу для заданного языка и имени.
    
    Args:
        language: Имя языка ("python", "typescript", etc.)
        golden_name: Имя файла без расширения
        
    Returns:
        Path к golden-файлу
    """
    # Находим корень проекта (где есть pyproject.toml)
    current = Path(__file__)
    while current.parent != current:
        if (current / "pyproject.toml").exists():
            break
        current = current.parent
    else:
        # Fallback: от текущего файла вверх
        current = Path(__file__).parent.parent.parent
    
    golden_dir = current / "tests" / "adapters" / language / "goldens"
    return golden_dir / f"{golden_name}.golden"


def _normalize_result(result: str) -> str:
    """
    Нормализует результат для стабильного сравнения.
    
    Args:
        result: Исходный результат
        
    Returns:
        Нормализованный результат
    """
    # Нормализуем переводы строк
    normalized = result.replace('\r\n', '\n').replace('\r', '\n')
    
    # Убираем trailing whitespace в конце файла, но сохраняем структуру
    normalized = normalized.rstrip() + '\n' if normalized.strip() else ''
    
    return normalized


def _create_diff_message(expected: str, actual: str, golden_file: Path) -> str:
    """
    Создает информативное сообщение об отличиях для AssertionError.
    
    Args:
        expected: Ожидаемое содержимое
        actual: Фактическое содержимое  
        golden_file: Путь к golden-файлу
        
    Returns:
        Форматированное сообщение с diff'ом
    """
    import difflib
    
    # Создаем unified diff
    diff_lines = list(difflib.unified_diff(
        expected.splitlines(keepends=True),
        actual.splitlines(keepends=True),
        fromfile=f"expected ({golden_file.name})",
        tofile="actual",
        lineterm=""
    ))
    
    if len(diff_lines) > 50:  # Ограничиваем очень длинные диффы
        diff_lines = diff_lines[:25] + ["\n... (diff truncated, showing first 25 lines) ...\n"] + diff_lines[-25:]
    
    diff_text = "".join(diff_lines)
    
    return (
        f"Golden test failed for {golden_file}\n"
        f"To update the golden file, run:\n"
        f"  PYTEST_UPDATE_GOLDENS=1 python -m pytest {golden_file.stem}\n"
        f"\nDiff:\n{diff_text}"
    )


def get_golden_dir(language: str) -> Path:
    """
    Получает директорию для golden-файлов заданного языка.
    Может быть полезно для внешних скриптов.
    
    Args:
        language: Имя языка
        
    Returns:
        Path к директории с golden-файлами
    """
    return _get_golden_file_path(language, "dummy").parent


def list_golden_files(language: Optional[str] = None) -> list[Path]:
    """
    Возвращает список всех golden-файлов для языка или всех языков.
    
    Args:
        language: Имя языка или None для всех языков
        
    Returns:
        Список путей к golden-файлам
    """
    if language:
        golden_dir = get_golden_dir(language)
        if golden_dir.exists():
            return list(golden_dir.glob("*.golden"))
        return []
    
    # Все языки
    result = []
    adapters_dir = Path(__file__).parent
    for lang_dir in adapters_dir.iterdir():
        if lang_dir.is_dir() and not lang_dir.name.startswith(("_", ".")):
            goldens_dir = lang_dir / "goldens"
            if goldens_dir.exists():
                result.extend(goldens_dir.glob("*.golden"))
    
    return result
