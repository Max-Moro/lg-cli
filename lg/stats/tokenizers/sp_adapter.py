from pathlib import Path
from typing import List
import logging

import sentencepiece as spm
from huggingface_hub import hf_hub_download

from .base import BaseTokenizer
from .model_cache import ModelCache

logger = logging.getLogger(__name__)

# Рекомендуемые универсальные модели SentencePiece
RECOMMENDED_MODELS = [
    "google/gemma-2-2b",       # Gemma токенизатор (Google)
    "meta-llama/Llama-2-7b-hf", # Llama 2 токенизатор
]

class SPAdapter(BaseTokenizer):
    """Адаптер для библиотеки SentencePiece."""
    
    def __init__(self, encoder: str, root: Path):
        super().__init__(encoder)
        self.root = root
        self.model_cache = ModelCache(root)
        
        self._sp = spm.SentencePieceProcessor()
        
        # Загружаем модель
        model_path = self._load_model(encoder)
        self._sp.load(str(model_path))
    
    def _load_model(self, model_spec: str) -> Path:
        """
        Загружает SentencePiece модель.
        
        Args:
            model_spec: Может быть:
                - Путь к локальному .model файлу: /path/to/model.spm
                - Имя модели на HF: google/gemma-2-2b
        
        Returns:
            Путь к загруженной модели
        """
        # Локальный файл
        local_path = Path(model_spec)
        if local_path.exists() and local_path.suffix in [".model", ".spm"]:
            logger.info(f"Loading SentencePiece model from local file: {local_path}")
            return local_path
        
        # Проверяем кеш
        if self.model_cache.is_model_cached("sentencepiece", model_spec):
            cache_dir = self.model_cache.get_model_cache_dir("sentencepiece", model_spec)
            # Ищем .model файл
            model_files = list(cache_dir.glob("*.model"))
            if model_files:
                logger.info(f"Loading SentencePiece model from cache: {model_files[0]}")
                return model_files[0]
        
        # Скачиваем с HuggingFace Hub
        logger.info(f"Downloading SentencePiece model '{model_spec}' from HuggingFace Hub...")
        try:
            cache_dir = self.model_cache.get_model_cache_dir("sentencepiece", model_spec)
            
            # Пробуем разные стандартные имена файлов
            for filename in ["tokenizer.model", "spiece.model", "sentencepiece.model"]:
                try:
                    model_file = hf_hub_download(
                        repo_id=model_spec,
                        filename=filename,
                        cache_dir=str(cache_dir),
                        local_dir=str(cache_dir),
                        local_dir_use_symlinks=False,
                    )
                    logger.info(f"SentencePiece model '{model_spec}' downloaded and cached successfully")
                    return Path(model_file)
                except Exception:
                    continue
            
            raise FileNotFoundError(
                f"Could not find SentencePiece model file in repository '{model_spec}'. "
                f"Tried: tokenizer.model, spiece.model, sentencepiece.model"
            )
        
        except Exception as e:
            raise RuntimeError(
                f"Failed to load SentencePiece model '{model_spec}'. "
                f"Ensure the model name is correct, it contains a .model file, "
                f"and you have internet connection."
            ) from e
    
    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self._sp.encode(text))
    
    def encode(self, text: str) -> List[int]:
        return self._sp.encode(text)
    
    def decode(self, token_ids: List[int]) -> str:
        return self._sp.decode(token_ids)
    
    @staticmethod
    def list_available_encoders(root: Path | None = None) -> List[str]:
        """
        Возвращает список доступных SentencePiece моделей.
        
        Включает:
        - Рекомендуемые модели
        - Уже скачанные модели
        - Подсказку про локальные файлы
        
        Args:
            root: Корень проекта
            
        Returns:
            Список имен моделей и подсказок
        """
        if root is None:
            # Без root возвращаем только рекомендуемые
            all_models = list(RECOMMENDED_MODELS)
        else:
            model_cache = ModelCache(root)
            cached = model_cache.list_cached_models("sentencepiece")
            
            # Объединяем рекомендуемые и кешированные
            all_models = list(RECOMMENDED_MODELS)
            for cached_model in cached:
                if cached_model not in all_models:
                    all_models.append(cached_model)
        
        # Добавляем подсказку про локальные файлы
        all_models.append("(or specify local file: /path/to/model.spm)")
        
        return all_models