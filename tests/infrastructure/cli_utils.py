"""
Утилиты для работы с CLI в тестах.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


# Дефолтные параметры токенизации для тестов
DEFAULT_TOKENIZER_LIB = "tiktoken"
DEFAULT_ENCODER = "cl100k_base"
DEFAULT_CTX_LIMIT = 128000


def run_cli(root: Path, *args: str) -> subprocess.CompletedProcess:
    """
    Запускает lg.cli с указанными аргументами в заданной директории.
    
    Автоматически добавляет обязательные параметры токенизации (--lib, --encoder, --ctx-limit)
    для команд report и render, если они не указаны явно.
    
    Args:
        root: Рабочая директория для выполнения команды
        *args: Аргументы командной строки для lg.cli
        
    Returns:
        CompletedProcess с результатами выполнения
    """
    # Преобразуем args в список для модификации
    args_list = list(args)
    
    # Проверяем, нужно ли добавлять параметры токенизации
    if _needs_tokenizer_params(args_list):
        args_list = _inject_tokenizer_params(args_list)
    
    env = os.environ.copy()
    return subprocess.run(
        [sys.executable, "-m", "lg.cli", *args_list],
        cwd=root, env=env, capture_output=True, text=True, encoding="utf-8"
    )


def _needs_tokenizer_params(args: list[str]) -> bool:
    """
    Проверяет, требует ли команда параметры токенизации.
    
    Параметры нужны для команд report и render, если они еще не указаны.
    """
    if not args:
        return False
    
    # Проверяем, является ли первый аргумент командой, требующей токенизацию
    command = args[0]
    if command not in ("report", "render"):
        return False
    
    # Проверяем, не указаны ли уже параметры токенизации
    has_lib = "--lib" in args
    has_encoder = "--encoder" in args
    has_ctx_limit = "--ctx-limit" in args
    
    # Если все параметры уже есть, добавлять ничего не нужно
    if has_lib and has_encoder and has_ctx_limit:
        return False
    
    return True


def _inject_tokenizer_params(args: list[str]) -> list[str]:
    """
    Добавляет дефолтные параметры токенизации в список аргументов.
    
    Вставляет параметры после команды (report/render) и target, но перед остальными опциями.
    """
    # Находим позицию для вставки (после команды и target)
    # Формат: command target [--options]
    insert_pos = 2  # После command и target
    
    # Если в args меньше 2 элементов, что-то не так, возвращаем как есть
    if len(args) < 2:
        return args
    
    result = args[:insert_pos]
    
    # Добавляем параметры токенизации, если их нет
    if "--lib" not in args:
        result.extend(["--lib", DEFAULT_TOKENIZER_LIB])
    
    if "--encoder" not in args:
        result.extend(["--encoder", DEFAULT_ENCODER])
    
    if "--ctx-limit" not in args:
        result.extend(["--ctx-limit", str(DEFAULT_CTX_LIMIT)])
    
    # Добавляем остальные аргументы
    result.extend(args[insert_pos:])
    
    return result


def jload(s: str):
    """
    Парсит JSON строку.
    
    Args:
        s: JSON строка
        
    Returns:
        Распарсенный объект
    """
    return json.loads(s)


__all__ = [
    "run_cli",
    "jload",
    "DEFAULT_TOKENIZER_LIB",
    "DEFAULT_ENCODER",
    "DEFAULT_CTX_LIMIT",
]