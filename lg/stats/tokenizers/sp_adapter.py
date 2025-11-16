from pathlib import Path
from typing import List
import logging

import sentencepiece as spm
from huggingface_hub import hf_hub_download

from .base import BaseTokenizer
from .model_cache import ModelCache

logger = logging.getLogger(__name__)

# Recommended universal SentencePiece models
# All models available for anonymous download from HuggingFace Hub
RECOMMENDED_MODELS = [
    "t5-small",              # T5 Small (compact, universal)
    "t5-base",               # T5 Base (larger vocab)
    "google/flan-t5-base",   # FLAN-T5 (improved T5, instruction-tuned)
    "google/mt5-base",       # mT5 (multilingual T5)
]

class SPAdapter(BaseTokenizer):
    """Adapter for SentencePiece library."""
    
    def __init__(self, encoder: str, root: Path):
        super().__init__(encoder)
        self.root = root
        self.model_cache = ModelCache(root)
        
        self._sp = spm.SentencePieceProcessor()

        # Load model
        model_path = self._load_model(encoder)
        self._sp.load(str(model_path))
    
    def _load_model(self, model_spec: str) -> Path:
        """
        Load SentencePiece model.

        Args:
            model_spec: Can be:
                - Path to local .model/.spm file: /path/to/model.spm
                - Path to directory with .model file: /path/to/model/
                - Model name on HF: google/gemma-2-2b

        Returns:
            Path to loaded model
        """
        # Local file
        local_path = Path(model_spec)
        if local_path.exists() and local_path.is_file() and local_path.suffix in [".model", ".spm"]:
            logger.info(f"Importing SentencePiece model from local file: {local_path}")
            try:
                # Import to cache for permanent reuse
                cache_name = self.model_cache.import_local_model("sentencepiece", local_path)
                logger.info(f"Model imported as '{cache_name}' and available for future use")

                # Load from cache
                cache_dir = self.model_cache.get_model_cache_dir("sentencepiece", cache_name)
                model_files = list(cache_dir.glob("*.model"))
                if not model_files:
                    model_files = list(cache_dir.glob("*.spm"))
                return model_files[0]
            except Exception as e:
                raise RuntimeError(f"Failed to import and load model from {local_path}: {e}") from e

        # Local directory
        if local_path.exists() and local_path.is_dir():
            logger.info(f"Importing SentencePiece model from local directory: {local_path}")
            try:
                # Import to cache for permanent reuse
                cache_name = self.model_cache.import_local_model("sentencepiece", local_path)
                logger.info(f"Model imported as '{cache_name}' and available for future use")

                # Load from cache
                cache_dir = self.model_cache.get_model_cache_dir("sentencepiece", cache_name)
                model_files = list(cache_dir.glob("*.model"))
                if not model_files:
                    model_files = list(cache_dir.glob("*.spm"))
                return model_files[0]
            except Exception as e:
                raise RuntimeError(f"Failed to import and load model from {local_path}: {e}") from e

        # Check cache
        if self.model_cache.is_model_cached("sentencepiece", model_spec):
            cache_dir = self.model_cache.get_model_cache_dir("sentencepiece", model_spec)
            # Look for .model file
            model_files = list(cache_dir.glob("*.model"))
            if model_files:
                logger.info(f"Loading SentencePiece model from cache: {model_files[0]}")
                return model_files[0]

        # Download from HuggingFace Hub
        logger.info(f"Downloading SentencePiece model '{model_spec}' from HuggingFace Hub...")
        try:
            cache_dir = self.model_cache.get_model_cache_dir("sentencepiece", model_spec)

            # Try different standard filenames
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
        Return list of available SentencePiece models.

        Includes:
        - Recommended models
        - Already downloaded models
        - Hint about local files

        Args:
            root: Project root

        Returns:
            List of model names and hints
        """
        if root is None:
            # Without root, return only recommended
            all_models = list(RECOMMENDED_MODELS)
        else:
            model_cache = ModelCache(root)
            cached = model_cache.list_cached_models("sentencepiece")

            # Combine recommended and cached
            all_models = list(RECOMMENDED_MODELS)
            for cached_model in cached:
                if cached_model not in all_models:
                    all_models.append(cached_model)

        # Add hint about local files
        all_models.append("(or specify local file: /path/to/model.spm)")

        return all_models