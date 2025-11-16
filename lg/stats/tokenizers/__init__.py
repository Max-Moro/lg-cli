from pathlib import Path
from typing import List

from .base import BaseTokenizer
from .tiktoken_adapter import TiktokenAdapter
from .hf_adapter import HFAdapter
from .sp_adapter import SPAdapter

def create_tokenizer(lib: str, encoder: str, root: Path) -> BaseTokenizer:
    """
    Create a tokenizer based on parameters.

    Args:
        lib: Library name (tiktoken, tokenizers, sentencepiece)
        encoder: Encoder/model name
        root: Project root

    Returns:
        Tokenizer instance

    Raises:
        ValueError: If library is unknown
    """
    if lib == "tiktoken":
        return TiktokenAdapter(encoder)
    elif lib == "tokenizers":
        return HFAdapter(encoder, root)
    elif lib == "sentencepiece":
        return SPAdapter(encoder, root)
    else:
        raise ValueError(
            f"Unknown tokenizer library: '{lib}'. "
            f"Supported: tiktoken, tokenizers, sentencepiece"
        )

def list_tokenizer_libs() -> List[str]:
    """Return list of supported tokenization libraries."""
    return ["tiktoken", "tokenizers", "sentencepiece"]

def list_encoders(lib: str, root: Path) -> List[str]:
    """
    Return list of available encoders for a library.

    Args:
        lib: Library name
        root: Project root (for cache access)

    Returns:
        List of encoder/model names

    Raises:
        ValueError: If library is unknown
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