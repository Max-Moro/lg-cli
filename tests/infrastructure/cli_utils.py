"""
Утилиты для работы с CLI в тестах.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    """
    Запускает lg.cli с указанными аргументами в заданной директории.
    
    Args:
        root: Рабочая директория для выполнения команды
        *args: Аргументы командной строки для lg.cli
        
    Returns:
        CompletedProcess с результатами выполнения
    """
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "lg.cli", *args],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8"
    )


def jload(s: str):
    """
    Парсит JSON строку.
    
    Args:
        s: JSON строка
        
    Returns:
        Распарсенный объект
    """
    return json.loads(s)