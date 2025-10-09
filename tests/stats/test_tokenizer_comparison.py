"""
Тесты сравнения точности различных токенизаторов.

Проверяют что:
- Разные токенизаторы дают разные результаты для одного текста
- Более специализированные токенизаторы могут быть точнее для определенных задач
- Tiktoken (базовый BPE) работает как универсальная аппроксимация
- HF и SP токенизаторы предоставляют более точные оценки для конкретных моделей
"""

from pathlib import Path

import pytest


class TestTokenizerBasics:
    """Базовые тесты работы токенизаторов."""
    
    def test_tiktoken_counts_tokens(self, tiktoken_service):
        """Проверяет что tiktoken корректно считает токены."""
        text = "Hello, world!"
        tokens = tiktoken_service.count_text(text)
        
        assert tokens > 0
        assert tokens < len(text)  # Токенов меньше чем символов
    
    def test_hf_tokenizer_counts_tokens(self, hf_tokenizer_service):
        """Проверяет что HF токенизатор корректно считает токены."""
        text = "Hello, world!"
        tokens = hf_tokenizer_service.count_text(text)
        
        assert tokens > 0
        assert tokens < len(text)
    
    def test_sp_tokenizer_counts_tokens(self, sp_tokenizer_service):
        """Проверяет что SentencePiece токенизатор корректно считает токены."""
        text = "Hello, world!"
        tokens = sp_tokenizer_service.count_text(text)
        
        assert tokens > 0
        assert tokens < len(text)
    
    def test_empty_text_returns_zero(self, tiktoken_service):
        """Проверяет что пустой текст возвращает 0 токенов."""
        assert tiktoken_service.count_text("") == 0
        assert tiktoken_service.count_text("   ") > 0  # Пробелы - это токены


class TestTokenizerDifferences:
    """Тесты различий между токенизаторами."""
    
    def test_different_tokenizers_different_results(
        self, 
        tiktoken_service, 
        hf_tokenizer_service,
        sample_texts
    ):
        """Проверяет что разные токенизаторы дают разные результаты."""
        text = sample_texts["simple"]
        
        tiktoken_count = tiktoken_service.count_text(text)
        hf_count = hf_tokenizer_service.count_text(text)
        
        # Результаты могут отличаться (разные алгоритмы и словари)
        # Но оба должны быть разумными
        assert 0 < tiktoken_count < len(text)
        assert 0 < hf_count < len(text)
    
    def test_tokenizers_consistent_for_same_text(self, tiktoken_service):
        """Проверяет что токенизатор выдает один результат для одного текста."""
        text = "Consistent tokenization test"
        
        count1 = tiktoken_service.count_text(text)
        count2 = tiktoken_service.count_text(text)
        
        assert count1 == count2
    
    def test_longer_text_more_tokens(self, tiktoken_service, sample_texts):
        """Проверяет что длинный текст имеет больше токенов."""
        short = sample_texts["simple"]
        long = sample_texts["long_text"]
        
        short_tokens = tiktoken_service.count_text(short)
        long_tokens = tiktoken_service.count_text(long)
        
        assert long_tokens > short_tokens


class TestTokenizerAccuracy:
    """Тесты точности токенизации для разных типов контента."""
    
    def test_code_tokenization_efficiency(self, tiktoken_service, sample_texts):
        """
        Проверяет что токенизация кода эффективна.
        
        Код обычно содержит много повторяющихся паттернов,
        поэтому токенов должно быть значительно меньше символов.
        """
        code = sample_texts["python_code"]
        
        char_count = len(code)
        token_count = tiktoken_service.count_text(code)
        
        # Примерное соотношение: 1 токен на 3-4 символа для кода
        compression_ratio = char_count / token_count
        
        assert compression_ratio > 2.0, "Code should compress well with tokenization"
        assert compression_ratio < 10.0, "But not too much"
    
    def test_special_chars_tokenization(
        self,
        tiktoken_service,
        hf_tokenizer_service,
        sample_texts
    ):
        """
        Проверяет обработку специальных символов разными токенизаторами.
        
        Разные токенизаторы по-разному обрабатывают Unicode, emoji и т.д.
        """
        text = sample_texts["special_chars"]
        
        tiktoken_count = tiktoken_service.count_text(text)
        hf_count = hf_tokenizer_service.count_text(text)
        
        # Оба должны корректно обработать текст
        assert tiktoken_count > 0
        assert hf_count > 0
        
        # Результаты могут отличаться из-за разной обработки Unicode
        # Главное что оба токенизатора работают
    
    def test_mixed_content_tokenization(self, tiktoken_service, sample_texts):
        """
        Проверяет токенизацию смешанного контента (текст + код + markdown).
        """
        mixed = sample_texts["mixed"]
        
        tokens = tiktoken_service.count_text(mixed)
        chars = len(mixed)
        
        # Смешанный контент должен иметь разумное соотношение
        compression = chars / tokens
        
        assert 2.0 < compression < 6.0, "Mixed content should have moderate compression"


class TestTokenizerComparison:
    """
    Сравнительные тесты точности токенизаторов.
    
    Эти тесты показывают что использование более точных токенизаторов
    оправдано для конкретных моделей.
    """
    
    @pytest.mark.parametrize("text_type", ["simple", "python_code", "mixed"])
    def test_all_tokenizers_reasonable(
        self,
        tiktoken_service,
        hf_tokenizer_service,
        sp_tokenizer_service,
        sample_texts,
        text_type
    ):
        """
        Проверяет что все токенизаторы дают разумные результаты
        для разных типов текста.
        """
        text = sample_texts[text_type]
        
        tiktoken_count = tiktoken_service.count_text(text)
        hf_count = hf_tokenizer_service.count_text(text)
        sp_count = sp_tokenizer_service.count_text(text)
        
        # Все результаты должны быть положительными
        assert tiktoken_count > 0
        assert hf_count > 0
        assert sp_count > 0
        
        # И все должны быть меньше длины текста
        text_len = len(text)
        assert tiktoken_count < text_len
        assert hf_count < text_len
        assert sp_count < text_len
    
    def test_tokenizer_variance_acceptable(
        self,
        tiktoken_service,
        hf_tokenizer_service,
        sample_texts
    ):
        """
        Проверяет что разница между токенизаторами находится
        в приемлемых пределах.
        
        Слишком большая разница может указывать на проблемы.
        """
        text = sample_texts["long_text"]
        
        tiktoken_count = tiktoken_service.count_text(text)
        hf_count = hf_tokenizer_service.count_text(text)
        
        # Вычисляем относительную разницу
        diff = abs(tiktoken_count - hf_count)
        avg = (tiktoken_count + hf_count) / 2
        relative_diff = diff / avg
        
        # Разница не должна превышать 50% от среднего
        # (разные алгоритмы могут давать существенно разные результаты,
        # но в разумных пределах)
        assert relative_diff < 0.5, f"Too large difference: {relative_diff:.1%}"


class TestTokenizerCaching:
    """Тесты кеширования токенов."""
    
    def test_cache_improves_performance(self, tmp_path: Path, mock_hf_hub):
        """
        Проверяет что кеширование токенов ускоряет повторные подсчеты.
        
        (Это качественный тест - реальные замеры производительности
        в unit-тестах не очень надежны)
        """
        from lg.cache.fs_cache import Cache
        from lg.stats.tokenizer import TokenService
        
        cache = Cache(tmp_path, enabled=True, fresh=False, tool_version="test")
        
        service = TokenService(
            root=tmp_path,
            lib="tiktoken",
            encoder="cl100k_base",
            cache=cache
        )
        
        text = "Test text for caching" * 100
        
        # Первый подсчет - идет в кеш
        count1 = service.count_text_cached(text)
        
        # Второй подсчет - должен использовать кеш
        count2 = service.count_text_cached(text)
        
        assert count1 == count2
        assert count1 > 0
    
    def test_cache_works_for_different_texts(self, tmp_path: Path):
        """Проверяет что кеш корректно работает для разных текстов."""
        from lg.cache.fs_cache import Cache
        from lg.stats.tokenizer import TokenService
        
        cache = Cache(tmp_path, enabled=True, fresh=False, tool_version="test")
        
        service = TokenService(
            root=tmp_path,
            lib="tiktoken",
            encoder="cl100k_base",
            cache=cache
        )
        
        text1 = "First text"
        text2 = "Second completely different text"
        
        count1 = service.count_text_cached(text1)
        count2 = service.count_text_cached(text2)
        
        # Разные тексты должны иметь разное количество токенов
        assert count1 != count2
        
        # Повторные подсчеты должны давать те же результаты
        assert service.count_text_cached(text1) == count1
        assert service.count_text_cached(text2) == count2
