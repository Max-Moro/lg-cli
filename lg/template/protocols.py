"""
Протоколы для модульного шаблонизатора.

Определяет интерфейсы для взаимодействия плагинов с компонентами ядра.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable, List


@runtime_checkable 
class TemplateRegistryProtocol(Protocol):
    """
    Протокол реестра шаблонизатора для использования в плагинах.
    
    Определяет методы, которые плагины могут использовать для:
    - Расширения контекстов токенов
    - Анализа зарегистрированных плагинов  
    - Получения информации о других компонентах системы
    """
    
    def register_tokens_in_context(self, context_name: str, token_names: List[str]) -> None:
        """
        Добавляет токены в существующий контекст.
        
        Args:
            context_name: Имя существующего контекста
            token_names: Имена токенов для добавления в контекст
            
        Raises:
            ValueError: Если контекст не найден
        """
        ...


__all__ = ["TemplateRegistryProtocol"]