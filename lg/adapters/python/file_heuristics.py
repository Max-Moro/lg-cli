"""
Python файловые эвристики для определения тривиальных __init__.py файлов.
Выделен в отдельный модуль для упрощения основного адаптера.
"""

from __future__ import annotations

from ..context import LightweightContext


def is_trivial_init_file(lightweight_ctx: LightweightContext) -> bool:
    """
    Определяет, является ли __init__.py файл тривиальным.
    
    Критерии тривиальности:
    - пустой файл
    - только 'pass' / '...'
    - только переэкспорт публичного API (относительные from-импорты, __all__)
    
    Комментарии сами по себе НЕ делают файл тривиальным (могут быть полезны).
    
    Args:
        lightweight_ctx: Облегченный контекст с информацией о файле
        
    Returns:
        True если файл является тривиальным __init__.py
    """
    # Только для __init__.py
    if lightweight_ctx.filename != "__init__.py":
        return False

    text = lightweight_ctx.raw_text or ""
    stripped = text.strip()

    # Пустой файл — тривиальный
    if stripped == "":
        return True

    lines = text.splitlines()

    # Выделяем строки без пустых и без комментариев для классификации
    non_comment_lines = []
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith("#"):
            # Комментарии не учитываем в классификации (они не делают файл тривиальным)
            continue
        non_comment_lines.append(ln)

    # Если в файле есть только комментарии — НЕ тривиальный
    if not non_comment_lines:
        return False

    def is_pass_or_ellipsis(s: str) -> bool:
        return s in ("pass", "...")

    def is_relative_from_import(s: str) -> bool:
        # from .pkg import X, Y
        if not s.startswith("from "):
            return False
        rest = s[5:].lstrip()
        return rest.startswith(".")

    def is_all_assign_start(s: str) -> bool:
        # __all__ = [...]
        return s.startswith("__all__")

    in_import_paren = False
    in_all_list = False

    for ln in non_comment_lines:
        if in_import_paren:
            # Продолжаем, пока не закроется группа импорта
            if ")" in ln:
                in_import_paren = False
            continue

        if in_all_list:
            # Разрешаем многострочный список в __all__
            if "]" in ln:
                in_all_list = False
            continue

        if is_pass_or_ellipsis(ln):
            continue

        if is_relative_from_import(ln):
            # Разрешаем многострочные импорты с '('
            if ln.endswith("(") or ln.endswith("\\") or "(" in ln and ")" not in ln:
                in_import_paren = True
            continue

        if is_all_assign_start(ln):
            # Разрешаем многострочный __all__ = [
            if "[" in ln and "]" not in ln:
                in_all_list = True
            continue

        # Любая другая конструкция делает файл нетривиальным
        return False

    # Если добрались сюда — все нетиповые строки допустимы → файл тривиальный
    return True


def should_skip_python_file(lightweight_ctx: LightweightContext, skip_trivial_inits: bool) -> bool:
    """
    Определяет, следует ли пропустить Python файл целиком.
    
    Args:
        lightweight_ctx: Облегченный контекст с информацией о файле
        skip_trivial_inits: Флаг пропуска тривиальных __init__.py файлов
        
    Returns:
        True если файл должен быть пропущен
    """
    # Пропускаем тривиальные __init__.py если включена соответствующая опция
    if skip_trivial_inits:
        if is_trivial_init_file(lightweight_ctx):
            return True

    return False