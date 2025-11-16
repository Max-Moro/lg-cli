from abc import ABC, abstractmethod
from typing import List
from pathlib import Path

class BaseTokenizer(ABC):
    """
    Abstract base class for all tokenizers.

    Unifies the interface for working with different tokenization libraries.
    """

    def __init__(self, encoder: str):
        """
        Args:
            encoder: Encoder name (for tiktoken) or model (for HF/SP)
        """
        self.encoder = encoder

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in text.

        Args:
            text: Original text

        Returns:
            Number of tokens
        """
        pass

    @abstractmethod
    def encode(self, text: str) -> List[int]:
        """
        Encode text into list of token IDs.

        Args:
            text: Original text

        Returns:
            List of token IDs
        """
        pass

    @abstractmethod
    def decode(self, token_ids: List[int]) -> str:
        """
        Decode token IDs back to text.

        Args:
            token_ids: List of token IDs

        Returns:
            Decoded text
        """
        pass

    @staticmethod
    @abstractmethod
    def list_available_encoders(root: Path | None = None) -> List[str]:
        """
        Return list of available encoders for this library.

        Includes:
        - Built-in encoders (for tiktoken)
        - Recommended models (for HF/SP)
        - Already downloaded models

        Returns:
            List of encoder/model names
        """
        pass

    @property
    def lib_name(self) -> str:
        """Tokenization library name (tiktoken, tokenizers, sentencepiece)."""
        return self.__class__.__name__.replace("Adapter", "").lower()

    @property
    def full_name(self) -> str:
        """Full tokenizer name in format 'lib:encoder'."""
        return f"{self.lib_name}:{self.encoder}"