from pathlib import Path
from typing import List
import logging

from tokenizers import Tokenizer
from huggingface_hub import hf_hub_download

from .base import BaseTokenizer
from .model_cache import ModelCache

logger = logging.getLogger(__name__)

# Рекомендуемые универсальные токенизаторы (не привязаны к продуктовым LLM)
# Все модели доступны для анонимного скачивания с HuggingFace Hub
RECOMMENDED_TOKENIZERS = [
    "gpt2",                         # GPT-2 BPE (универсальный для кода и текста)
    "roberta-base",                 # RoBERTa BPE (улучшенный GPT-2)
    "t5-base",                      # T5 SentencePiece-based (универсальный)
    "EleutherAI/gpt-neo-125m",      # GPT-Neo BPE (открытая альтернатива GPT)
    "microsoft/phi-2",              # Phi-2 (современная компактная модель)
    "mistralai/Mistral-7B-v0.1",    # Mistral (современная open-source модель)
]

class HFAdapter(BaseTokenizer):
    """Адаптер для библиотеки tokenizers (HuggingFace)."""
    
    def __init__(self, encoder: str, root: Path):
        super().__init__(encoder)
        self.root = root
        self.model_cache = ModelCache(root)
        
        # Загружаем токенизатор
        self._tokenizer = self._load_tokenizer(encoder)
    
    def _load_tokenizer(self, model_spec: str) -> Tokenizer:
        """
        Загружает токенизатор из локального файла, кеша или HuggingFace Hub.
        
        Args:
            model_spec: Может быть:
                - Путь к локальному файлу tokenizer.json: /path/to/tokenizer.json
                - Путь к директории с tokenizer.json: /path/to/model/
                - Имя модели на HF: gpt2, mistralai/Mistral-7B-v0.1
            
        Returns:
            Загруженный токенизатор
        """
        # Локальный файл или директория
        local_path = Path(model_spec)
        
        # Проверяем файл tokenizer.json напрямую
        if local_path.exists() and local_path.is_file() and local_path.suffix == ".json":
            logger.info(f"Loading tokenizer from local file: {local_path}")
            try:
                return Tokenizer.from_file(str(local_path))
            except Exception as e:
                raise RuntimeError(f"Failed to load tokenizer from local file {local_path}: {e}") from e
        
        # Проверяем директорию с tokenizer.json
        if local_path.exists() and local_path.is_dir():
            tokenizer_file = local_path / "tokenizer.json"
            if tokenizer_file.exists():
                logger.info(f"Loading tokenizer from local directory: {tokenizer_file}")
                try:
                    return Tokenizer.from_file(str(tokenizer_file))
                except Exception as e:
                    raise RuntimeError(f"Failed to load tokenizer from {tokenizer_file}: {e}") from e
            else:
                raise FileNotFoundError(
                    f"Directory {local_path} exists but does not contain tokenizer.json"
                )
        
        # Проверяем кеш
        if self.model_cache.is_model_cached("tokenizers", model_spec):
            cache_dir = self.model_cache.get_model_cache_dir("tokenizers", model_spec)
            tokenizer_path = cache_dir / "tokenizer.json"
            logger.info(f"Loading tokenizer from cache: {tokenizer_path}")
            return Tokenizer.from_file(str(tokenizer_path))
        
        # Скачиваем с HuggingFace Hub
        logger.info(f"Downloading tokenizer '{model_spec}' from HuggingFace Hub...")
        try:
            cache_dir = self.model_cache.get_model_cache_dir("tokenizers", model_spec)
            
            # Скачиваем tokenizer.json
            tokenizer_file = hf_hub_download(
                repo_id=model_spec,
                filename="tokenizer.json",
                cache_dir=str(cache_dir),
                local_dir=str(cache_dir),
                local_dir_use_symlinks=False,
            )
            
            tokenizer = Tokenizer.from_file(tokenizer_file)
            logger.info(f"Tokenizer '{model_spec}' downloaded and cached successfully")
            return tokenizer
        
        except Exception as e:
            raise RuntimeError(
                f"Failed to load tokenizer '{model_spec}' from HuggingFace Hub. "
                f"Ensure the model name is correct and you have internet connection. "
                f"Or provide a path to local tokenizer.json file."
            ) from e
    
    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        encoding = self._tokenizer.encode(text)
        return len(encoding.ids)
    
    def encode(self, text: str) -> List[int]:
        return self._tokenizer.encode(text).ids
    
    def decode(self, token_ids: List[int]) -> str:
        return self._tokenizer.decode(token_ids)
    
    @staticmethod
    def list_available_encoders(root: Path | None = None) -> List[str]:
        """
        Возвращает список доступных токенизаторов.
        
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
            all_models = list(RECOMMENDED_TOKENIZERS)
        else:
            model_cache = ModelCache(root)
            cached = model_cache.list_cached_models("tokenizers")
            
            # Объединяем рекомендуемые и кешированные (без дубликатов)
            all_models = list(RECOMMENDED_TOKENIZERS)
            for cached_model in cached:
                if cached_model not in all_models:
                    all_models.append(cached_model)
        
        # Добавляем подсказку про локальные файлы
        all_models.append("(or specify local file: /path/to/tokenizer.json or /path/to/model/)")
        
        return all_models