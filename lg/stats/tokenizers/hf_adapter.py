from pathlib import Path
from typing import List
import logging

from tokenizers import Tokenizer
from huggingface_hub import hf_hub_download

from .base import BaseTokenizer
from .model_cache import ModelCache

logger = logging.getLogger(__name__)

# Recommended universal tokenizers (not tied to specific LLMs)
# All models available for anonymous download from HuggingFace Hub
RECOMMENDED_TOKENIZERS = [
    "gpt2",                         # GPT-2 BPE (universal for code and text)
    "roberta-base",                 # RoBERTa BPE (improved GPT-2)
    "t5-base",                      # T5 SentencePiece-based (universal)
    "EleutherAI/gpt-neo-125m",      # GPT-Neo BPE (open-source GPT alternative)
    "microsoft/phi-2",              # Phi-2 (modern compact model)
    "mistralai/Mistral-7B-v0.1",    # Mistral (modern open-source model)
]

class HFAdapter(BaseTokenizer):
    """Adapter for tokenizers library (HuggingFace)."""
    
    def __init__(self, encoder: str, root: Path):
        super().__init__(encoder)
        self.root = root
        self.model_cache = ModelCache(root)

        # Load tokenizer
        self._tokenizer = self._load_tokenizer(encoder)
    
    def _load_tokenizer(self, model_spec: str) -> Tokenizer:
        """
        Load tokenizer from local file, cache, or HuggingFace Hub.

        Args:
            model_spec: Can be:
                - Path to local tokenizer.json file: /path/to/tokenizer.json
                - Path to directory with tokenizer.json: /path/to/model/
                - Model name on HF: gpt2, mistralai/Mistral-7B-v0.1

        Returns:
            Loaded tokenizer
        """
        # Local file or directory
        local_path = Path(model_spec)

        # Check tokenizer.json file directly
        if local_path.exists() and local_path.is_file() and local_path.suffix == ".json":
            logger.info(f"Importing tokenizer from local file: {local_path}")
            try:
                # Import to cache for permanent reuse
                cache_name = self.model_cache.import_local_model("tokenizers", local_path)
                logger.info(f"Tokenizer imported as '{cache_name}' and available for future use")

                # Load from cache
                cache_dir = self.model_cache.get_model_cache_dir("tokenizers", cache_name)
                return Tokenizer.from_file(str(cache_dir / "tokenizer.json"))
            except Exception as e:
                raise RuntimeError(f"Failed to import and load tokenizer from {local_path}: {e}") from e

        # Check directory with tokenizer.json
        if local_path.exists() and local_path.is_dir():
            tokenizer_file = local_path / "tokenizer.json"
            if tokenizer_file.exists():
                logger.info(f"Importing tokenizer from local directory: {local_path}")
                try:
                    # Import to cache for permanent reuse
                    cache_name = self.model_cache.import_local_model("tokenizers", local_path)
                    logger.info(f"Tokenizer imported as '{cache_name}' and available for future use")

                    # Load from cache
                    cache_dir = self.model_cache.get_model_cache_dir("tokenizers", cache_name)
                    return Tokenizer.from_file(str(cache_dir / "tokenizer.json"))
                except Exception as e:
                    raise RuntimeError(f"Failed to import and load tokenizer from {local_path}: {e}") from e
            else:
                raise FileNotFoundError(
                    f"Directory {local_path} exists but does not contain tokenizer.json"
                )

        # Check cache
        if self.model_cache.is_model_cached("tokenizers", model_spec):
            cache_dir = self.model_cache.get_model_cache_dir("tokenizers", model_spec)
            tokenizer_path = cache_dir / "tokenizer.json"
            logger.info(f"Loading tokenizer from cache: {tokenizer_path}")
            return Tokenizer.from_file(str(tokenizer_path))

        # Download from HuggingFace Hub
        logger.info(f"Downloading tokenizer '{model_spec}' from HuggingFace Hub...")
        try:
            cache_dir = self.model_cache.get_model_cache_dir("tokenizers", model_spec)

            # Download tokenizer.json
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
        Return list of available tokenizers.

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
            all_models = list(RECOMMENDED_TOKENIZERS)
        else:
            model_cache = ModelCache(root)
            cached = model_cache.list_cached_models("tokenizers")

            # Combine recommended and cached (without duplicates)
            all_models = list(RECOMMENDED_TOKENIZERS)
            for cached_model in cached:
                if cached_model not in all_models:
                    all_models.append(cached_model)

        # Add hint about local files
        all_models.append("(or specify local file: /path/to/tokenizer.json)")

        return all_models