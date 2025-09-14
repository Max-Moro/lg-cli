"""
TypeScript файловые эвристики для определения barrel files.
Выделен в отдельный модуль для упрощения основного адаптера.
"""

from __future__ import annotations

from ..context import LightweightContext
from ..tree_sitter_support import TreeSitterDocument


def is_barrel_file(lightweight_ctx: LightweightContext, adapter, tokenizer) -> bool:
    """
    Определяет, является ли файл barrel file (index.ts или содержит только реэкспорты).
    Использует ленивую инициализацию - сначала простые эвристики, затем парсинг если нужно.
    
    Args:
        lightweight_ctx: Облегченный контекст с информацией о файле
        adapter: Адаптер для создания документа при необходимости
        tokenizer: Токенайзер для парсинга
        
    Returns:
        True если файл является barrel file
    """
    # Быстрая проверка по имени файла
    if lightweight_ctx.filename in ("index.ts", "index.tsx"):
        return True
    
    # Анализируем содержимое текстуально - если большинство строк содержат export ... from
    lines = lightweight_ctx.raw_text.split('\n')
    export_lines = 0
    non_empty_lines = 0
    
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
            non_empty_lines += 1
            if 'export' in stripped and 'from' in stripped:
                export_lines += 1
    
    # Если нет значимых строк, не barrel file
    if non_empty_lines == 0:
        return False
    
    # Эвристика: если больше 70% строк - реэкспорты, считаем barrel file
    export_ratio = export_lines / non_empty_lines
    
    # Если очевидно barrel file (много реэкспортов), возвращаем True
    if export_ratio > 0.7:
        return True
    
    # Если очевидно НЕ barrel file (мало реэкспортов), возвращаем False
    if export_ratio < 0.3:
        return False
    
    # Для промежуточных случаев (30-70%) используем ленивую инициализацию Tree-sitter
    # для более точного анализа структуры файла
    try:
        full_context = lightweight_ctx.get_full_context(adapter, tokenizer)
        return _deep_barrel_file_analysis(full_context.doc)
    except Exception:
        # Если Tree-sitter парсинг не удался, полагаемся на текстовую эвристику
        return export_ratio > 0.5


def _deep_barrel_file_analysis(doc: TreeSitterDocument) -> bool:
    """
    Глубокий анализ barrel file через Tree-sitter парсинг.
    Вызывается только в сложных случаях.
    
    Args:
        doc: Разобранный Tree-sitter документ
        
    Returns:
        True если документ является barrel file
    """
    try:
        # Ищем все export statements
        exports = doc.query("exports")
        export_count = len(exports)
        
        # Ищем re-export statements (export ... from ...)
        reexport_count = 0
        for node, capture_name in exports:
            node_text = doc.get_node_text(node)
            if ' from ' in node_text:
                reexport_count += 1
        
        # Также ищем обычные объявления (functions, classes, interfaces)
        functions = doc.query("functions")
        classes = doc.query("classes")
        interfaces = doc.query("interfaces")
        
        declaration_count = len(functions) + len(classes) + len(interfaces)
        
        # Barrel file если:
        # 1. Много реэкспортов и мало собственных объявлений
        # 2. Или очень высокий процент реэкспортов
        if export_count > 0:
            reexport_ratio = reexport_count / export_count
            return reexport_ratio > 0.6 and declaration_count < 3
        
        return False
        
    except Exception:
        # При ошибках парсинга возвращаем False
        return False


def should_skip_typescript_file(lightweight_ctx: LightweightContext, skip_barrel_files: bool, adapter, tokenizer) -> bool:
    """
    Определяет, следует ли пропустить TypeScript файл целиком.
    
    Args:
        lightweight_ctx: Облегченный контекст с информацией о файле
        skip_barrel_files: Флаг пропуска barrel files
        adapter: Адаптер для создания документа при необходимости
        tokenizer: Токенайзер для парсинга
        
    Returns:
        True если файл должен быть пропущен
    """
    # Пропускаем barrel files если включена соответствующая опция
    if skip_barrel_files:
        if is_barrel_file(lightweight_ctx, adapter, tokenizer):
            return True
    
    # Можно добавить другие эвристики пропуска для TypeScript
    return False