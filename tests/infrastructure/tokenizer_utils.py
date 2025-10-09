"""
Утилиты для работы с токенизаторами в тестах.

Предоставляет хелперы для:
- Создания токенизаторов с различными конфигурациями
- Сравнения результатов токенизации
- Работы с кешем токенов
"""

from pathlib import Path

from lg.cache.fs_cache import Cache
from lg.stats.tokenizer import TokenService


def create_tokenizer(
    root: Path,
    lib: str = "tiktoken",
    encoder: str = "cl100k_base",
    ctx_limit: int = 128000,
    use_cache: bool = False
) -> TokenService:
    """
    Создает TokenService для тестов.
    
    Args:
        root: Корень проекта
        lib: Библиотека токенизации
        encoder: Энкодер
        ctx_limit: Размер контекстного окна
        use_cache: Использовать ли кеш
        
    Returns:
        Настроенный TokenService
    """
    cache = None
    if use_cache:
        cache = Cache(root, enabled=True, fresh=False, tool_version="test")
    
    return TokenService(
        root=root,
        lib=lib,
        encoder=encoder,
        cache=cache
    )


def compare_tokenizers(
    text: str,
    tokenizers: list[TokenService]
) -> dict[str, int]:
    """
    Сравнивает результаты токенизации для разных токенизаторов.
    
    Args:
        text: Текст для токенизации
        tokenizers: Список токенизаторов для сравнения
        
    Returns:
        Словарь {tokenizer_name: token_count}
    """
    results = {}
    for tokenizer in tokenizers:
        name = f"{tokenizer.lib}:{tokenizer.encoder}"
        results[name] = tokenizer.count_text(text)
    
    return results


def get_compression_ratio(text: str, tokenizer: TokenService) -> float:
    """
    Вычисляет коэффициент сжатия текста при токенизации.
    
    Args:
        text: Исходный текст
        tokenizer: Токенизатор
        
    Returns:
        Соотношение символов к токенам (chars/tokens)
    """
    if not text:
        return 0.0
    
    char_count = len(text)
    token_count = tokenizer.count_text(text)
    
    if token_count == 0:
        return 0.0
    
    return char_count / token_count


def estimate_tokens_for_file(file_path: Path, tokenizer: TokenService) -> int:
    """
    Оценивает количество токенов в файле.
    
    Args:
        file_path: Путь к файлу
        tokenizer: Токенизатор
        
    Returns:
        Количество токенов
    """
    content = file_path.read_text(encoding="utf-8")
    return tokenizer.count_text(content)


def count_tokens_with_cache_check(
    text: str,
    tokenizer: TokenService
) -> tuple[int, bool]:
    """
    Подсчитывает токены и проверяет использовался ли кеш.
    
    Args:
        text: Текст для токенизации
        tokenizer: Токенизатор с кешем
        
    Returns:
        Tuple (количество токенов, был ли использован кеш)
    """
    if not tokenizer.cache:
        # Без кеша
        return tokenizer.count_text(text), False
    
    cache_key = f"{tokenizer.lib}:{tokenizer.encoder}"
    
    # Проверяем наличие в кеше
    was_cached = tokenizer.cache.get_text_tokens(text, cache_key) is not None
    
    # Подсчитываем токены (с кешированием)
    token_count = tokenizer.count_text_cached(text)
    
    return token_count, was_cached


__all__ = [
    "create_tokenizer",
    "compare_tokenizers",
    "get_compression_ratio",
    "estimate_tokens_for_file",
    "count_tokens_with_cache_check",
]
