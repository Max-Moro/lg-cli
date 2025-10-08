import tiktoken
from typing import List
from pathlib import Path
from .base import BaseTokenizer

class TiktokenAdapter(BaseTokenizer):
    """Адаптер для библиотеки tiktoken (OpenAI)."""
    
    def __init__(self, encoder: str, ctx_limit: int):
        super().__init__(encoder, ctx_limit)
        
        try:
            self._enc = tiktoken.get_encoding(encoder)
        except Exception as e:
            available = tiktoken.list_encoding_names()
            raise ValueError(
                f"Unknown tiktoken encoding '{encoder}'. "
                f"Available: {', '.join(available)}"
            ) from e
    
    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self._enc.encode(text))
    
    def encode(self, text: str) -> List[int]:
        return self._enc.encode(text)
    
    def decode(self, token_ids: List[int]) -> str:
        return self._enc.decode(token_ids)
    
    @staticmethod
    def list_available_encoders(root: Path | None = None) -> List[str]:
        """Возвращает список встроенных энкодеров tiktoken."""
        return tiktoken.list_encoding_names()