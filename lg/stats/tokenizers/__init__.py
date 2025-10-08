from pathlib import Path
from typing import List

from .base import BaseTokenizer
from .tiktoken_adapter import TiktokenAdapter
from .hf_adapter import HFAdapter
from .sp_adapter import SPAdapter

def create_tokenizer(lib: str, encoder: str, ctx_limit: int, root: Path) -> BaseTokenizer:
    """
    Создает токенизатор по параметрам.
    
    Args:
        lib: Имя библиотеки (tiktoken, tokenizers, sentencepiece)
        encoder: Имя энкодера/модели
        ctx_limit: Размер контекстного окна в токенах
        root: Корень проекта
        
    Returns:
        Инстанс токенизатора
        
    Raises:
        ValueError: Если библиотека неизвестна
    """
    if lib == "tiktoken":
        return TiktokenAdapter(encoder, ctx_limit)
    elif lib == "tokenizers":
        return HFAdapter(encoder, ctx_limit, root)
    elif lib == "sentencepiece":
        return SPAdapter(encoder, ctx_limit, root)
    else:
        raise ValueError(
            f"Unknown tokenizer library: '{lib}'. "
            f"Supported: tiktoken, tokenizers, sentencepiece"
        )

def list_tokenizer_libs() -> List[str]:
    """Возвращает список поддерживаемых библиотек токенизации."""
    return ["tiktoken", "tokenizers", "sentencepiece"]

def list_encoders(lib: str, root: Path) -> List[str]:
    """
    Возвращает список доступных энкодеров для библиотеки.
    
    Args:
        lib: Имя библиотеки
        root: Корень проекта (для доступа к кешу)
        
    Returns:
        Список имен энкодеров/моделей
        
    Raises:
        ValueError: Если библиотека неизвестна
    """
    if lib == "tiktoken":
        return TiktokenAdapter.list_available_encoders(root)
    elif lib == "tokenizers":
        return HFAdapter.list_available_encoders(root)
    elif lib == "sentencepiece":
        return SPAdapter.list_available_encoders(root)
    else:
        raise ValueError(
            f"Unknown tokenizer library: '{lib}'. "
            f"Supported: tiktoken, tokenizers, sentencepiece"
        )

__all__ = [
    "BaseTokenizer",
    "create_tokenizer",
    "list_tokenizer_libs",
    "list_encoders",
]