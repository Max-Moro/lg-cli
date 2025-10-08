from abc import ABC, abstractmethod
from typing import List
from pathlib import Path

class BaseTokenizer(ABC):
    """
    Абстрактный базовый класс для всех токенизаторов.
    
    Унифицирует интерфейс работы с разными библиотеками токенизации.
    """
    
    def __init__(self, encoder: str):
        """
        Args:
            encoder: Имя энкодера (для tiktoken) или модели (для HF/SP)
        """
        self.encoder = encoder
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Подсчитывает количество токенов в тексте.
        
        Args:
            text: Исходный текст
            
        Returns:
            Количество токенов
        """
        pass
    
    @abstractmethod
    def encode(self, text: str) -> List[int]:
        """
        Кодирует текст в список token IDs.
        
        Args:
            text: Исходный текст
            
        Returns:
            Список token IDs
        """
        pass
    
    @abstractmethod
    def decode(self, token_ids: List[int]) -> str:
        """
        Декодирует token IDs обратно в текст.
        
        Args:
            token_ids: Список token IDs
            
        Returns:
            Декодированный текст
        """
        pass
    
    @staticmethod
    @abstractmethod
    def list_available_encoders(root: Path | None = None) -> List[str]:
        """
        Возвращает список доступных энкодеров для данной библиотеки.
        
        Включает:
        - Встроенные энкодеры (для tiktoken)
        - Рекомендуемые модели (для HF/SP)
        - Уже скачанные модели
        
        Returns:
            Список имен энкодеров/моделей
        """
        pass
    
    @property
    def lib_name(self) -> str:
        """Имя библиотеки токенизации (tiktoken, tokenizers, sentencepiece)."""
        return self.__class__.__name__.replace("Adapter", "").lower()
    
    @property
    def full_name(self) -> str:
        """Полное имя токенизатора в формате 'lib:encoder'."""
        return f"{self.lib_name}:{self.encoder}"