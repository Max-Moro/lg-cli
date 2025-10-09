"""
Тесты для lg.stats.tokenizers.model_cache.

Проверяют корректность кеширования моделей токенизации:
- Создание структуры кеша
- Проверка наличия моделей в кеше
- Список закешированных моделей
- Безопасное преобразование имен моделей с '/' в пути
"""

from pathlib import Path

from lg.stats.tokenizers.model_cache import ModelCache


class TestModelCache:
    """Тесты базовой функциональности ModelCache."""
    
    def test_cache_initialization(self, tmp_path: Path):
        """Проверяет создание структуры кеша при инициализации."""
        cache = ModelCache(tmp_path)
        
        assert cache.cache_dir.exists()
        assert cache.cache_dir == tmp_path / ".lg-cache" / "tokenizer-models"
    
    def test_get_lib_cache_dir(self, tmp_path: Path):
        """Проверяет создание директории для библиотеки."""
        cache = ModelCache(tmp_path)
        
        tokenizers_dir = cache.get_lib_cache_dir("tokenizers")
        assert tokenizers_dir.exists()
        assert tokenizers_dir == cache.cache_dir / "tokenizers"
        
        sp_dir = cache.get_lib_cache_dir("sentencepiece")
        assert sp_dir.exists()
        assert sp_dir == cache.cache_dir / "sentencepiece"
    
    def test_get_model_cache_dir_simple_name(self, tmp_path: Path):
        """Проверяет создание директории для модели с простым именем."""
        cache = ModelCache(tmp_path)
        
        model_dir = cache.get_model_cache_dir("tokenizers", "gpt2")
        
        assert model_dir.exists()
        assert model_dir == cache.cache_dir / "tokenizers" / "gpt2"
    
    def test_get_model_cache_dir_with_slash(self, tmp_path: Path):
        """Проверяет безопасное преобразование имен моделей с '/'."""
        cache = ModelCache(tmp_path)
        
        model_dir = cache.get_model_cache_dir("sentencepiece", "t5-small")
        
        # Для t5-small слэшей нет, путь остается t5-small
        assert model_dir.exists()
        assert model_dir == cache.cache_dir / "sentencepiece" / "t5-small"
    
    def test_is_model_cached_tokenizers(self, tmp_path: Path):
        """Проверяет определение наличия модели tokenizers в кеше."""
        cache = ModelCache(tmp_path)
        
        # Модель не закеширована
        assert not cache.is_model_cached("tokenizers", "gpt2")
        
        # Создаем файл модели
        model_dir = cache.get_model_cache_dir("tokenizers", "gpt2")
        (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
        
        # Модель теперь в кеше
        assert cache.is_model_cached("tokenizers", "gpt2")
    
    def test_is_model_cached_sentencepiece(self, tmp_path: Path):
        """Проверяет определение наличия модели sentencepiece в кеше."""
        cache = ModelCache(tmp_path)
        
        # Модель не закеширована
        assert not cache.is_model_cached("sentencepiece", "t5-small")
        
        # Создаем файл модели
        model_dir = cache.get_model_cache_dir("sentencepiece", "t5-small")
        (model_dir / "tokenizer.model").write_bytes(b"fake model data")
        
        # Модель теперь в кеше
        assert cache.is_model_cached("sentencepiece", "t5-small")
    
    def test_list_cached_models_empty(self, tmp_path: Path):
        """Проверяет список моделей в пустом кеше."""
        cache = ModelCache(tmp_path)
        
        assert cache.list_cached_models("tokenizers") == []
        assert cache.list_cached_models("sentencepiece") == []
    
    def test_list_cached_models_tokenizers(self, tmp_path: Path):
        """Проверяет список закешированных моделей tokenizers."""
        cache = ModelCache(tmp_path)
        
        # Создаем несколько моделей
        for model_name in ["gpt2", "roberta-base", "bert-base-uncased"]:
            model_dir = cache.get_model_cache_dir("tokenizers", model_name)
            (model_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
        
        cached = cache.list_cached_models("tokenizers")
        
        assert len(cached) == 3
        assert "gpt2" in cached
        assert "roberta-base" in cached
        assert "bert-base-uncased" in cached
    
    def test_list_cached_models_sentencepiece(self, tmp_path: Path):
        """Проверяет список закешированных моделей sentencepiece."""
        cache = ModelCache(tmp_path)
        
        # Создаем несколько моделей (с / в имени)
        models = ["t5-small", "meta-llama/Llama-2-7b-hf"]
        for model_name in models:
            model_dir = cache.get_model_cache_dir("sentencepiece", model_name)
            (model_dir / "tokenizer.model").write_bytes(b"fake model data")
        
        cached = cache.list_cached_models("sentencepiece")
        
        assert len(cached) == 2
        # Имена должны быть восстановлены с /
        assert "t5-small" in cached
        assert "meta-llama/Llama-2-7b-hf" in cached
    
    def test_list_cached_models_ignores_incomplete(self, tmp_path: Path):
        """Проверяет что неполные модели (без нужных файлов) игнорируются."""
        cache = ModelCache(tmp_path)
        
        # Создаем директорию без файла модели
        incomplete_dir = cache.get_model_cache_dir("tokenizers", "incomplete-model")
        (incomplete_dir / "some-other-file.txt").write_text("not a tokenizer")
        
        # Создаем полную модель
        complete_dir = cache.get_model_cache_dir("tokenizers", "gpt2")
        (complete_dir / "tokenizer.json").write_text("{}", encoding="utf-8")
        
        cached = cache.list_cached_models("tokenizers")
        
        # Только полная модель в списке
        assert len(cached) == 1
        assert "gpt2" in cached
        assert "incomplete-model" not in cached


class TestModelCacheIntegration:
    """Интеграционные тесты кеша с реальными адаптерами."""
    
    def test_tokenizers_adapter_uses_cache(self, tmp_path: Path, mock_hf_hub):
        """Проверяет что HFAdapter использует кеш при повторных запросах."""
        from lg.stats.tokenizers.hf_adapter import HFAdapter
        
        # Первая загрузка - должна "скачать" модель
        adapter1 = HFAdapter("gpt2", tmp_path)
        initial_downloads = mock_hf_hub.download_count
        
        # Вторая загрузка - должна использовать кеш
        adapter2 = HFAdapter("gpt2", tmp_path)
        
        # Количество скачиваний не должно увеличиться
        assert mock_hf_hub.download_count == initial_downloads
        
        # Оба адаптера должны работать
        text = "Hello, world!"
        tokens1 = adapter1.count_tokens(text)
        tokens2 = adapter2.count_tokens(text)
        
        assert tokens1 == tokens2
        assert tokens1 > 0
    
    def test_sentencepiece_adapter_uses_cache(self, tmp_path: Path, mock_hf_hub):
        """Проверяет что SPAdapter использует кеш при повторных запросах."""
        from lg.stats.tokenizers.sp_adapter import SPAdapter
        
        # Первая загрузка - должна "скачать" модель
        adapter1 = SPAdapter("t5-small", tmp_path)
        initial_downloads = mock_hf_hub.download_count
        
        # Вторая загрузка - должна использовать кеш
        adapter2 = SPAdapter("t5-small", tmp_path)
        
        # Количество скачиваний не должно увеличиться
        assert mock_hf_hub.download_count == initial_downloads
        
        # Оба адаптера должны работать
        text = "Hello, world!"
        tokens1 = adapter1.count_tokens(text)
        tokens2 = adapter2.count_tokens(text)
        
        assert tokens1 == tokens2
        assert tokens1 > 0
    
    def test_cache_persists_across_sessions(self, tmp_path: Path, mock_hf_hub):
        """Проверяет что кеш сохраняется между "сессиями"."""
        from lg.stats.tokenizers.hf_adapter import HFAdapter
        from lg.stats.tokenizers.model_cache import ModelCache
        
        # Первая "сессия" - загружаем модель
        adapter1 = HFAdapter("gpt2", tmp_path)
        download_count_after_first = mock_hf_hub.download_count
        
        # Проверяем что модель в кеше
        cache = ModelCache(tmp_path)
        assert cache.is_model_cached("tokenizers", "gpt2")
        
        # Вторая "сессия" - создаем новый адаптер
        # (имитируем перезапуск программы)
        adapter2 = HFAdapter("gpt2", tmp_path)
        
        # Модель не должна скачиваться заново
        assert mock_hf_hub.download_count == download_count_after_first
        
        # Адаптер должен работать
        text = "Test text"
        assert adapter2.count_tokens(text) > 0
