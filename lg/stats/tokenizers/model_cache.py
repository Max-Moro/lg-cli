import logging
from pathlib import Path

from ...git.gitignore import ensure_gitignore_entry

logger = logging.getLogger(__name__)

class ModelCache:
    """
    Manager for cache of downloaded tokenization models.

    Stores models in .lg-cache/tokenizer-models/{lib}/{model_name}/
    """

    def __init__(self, root: Path):
        """
        Args:
            root: Project root
        """
        self.root = root
        self.cache_dir = root / ".lg-cache" / "tokenizer-models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Ensure .gitignore entry exists
        ensure_gitignore_entry(root, ".lg-cache/", comment="LG cache directory")

    def get_lib_cache_dir(self, lib: str) -> Path:
        """Return cache directory for a specific library."""
        lib_dir = self.cache_dir / lib
        lib_dir.mkdir(parents=True, exist_ok=True)
        return lib_dir

    def get_model_cache_dir(self, lib: str, model_name: str) -> Path:
        """
        Return cache directory for a specific model.

        Args:
            lib: Library name (tokenizers, sentencepiece)
            model_name: Model name (can contain /, e.g., google/gemma-2-2b)

        Returns:
            Path to model cache directory
        """
        # Safe transformation of model name to path
        safe_name = model_name.replace("/", "--")
        model_dir = self.get_lib_cache_dir(lib) / safe_name
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir
    
    def is_model_cached(self, lib: str, model_name: str) -> bool:
        """
        Check if model is cached.

        Args:
            lib: Library name
            model_name: Model name

        Returns:
            True if model exists in cache
        """
        model_dir = self.get_model_cache_dir(lib, model_name)

        # For tokenizers check for tokenizer.json
        if lib == "tokenizers":
            return (model_dir / "tokenizer.json").exists()

        # For sentencepiece check for .model file
        if lib == "sentencepiece":
            return any(model_dir.glob("*.model"))

        return False

    def list_cached_models(self, lib: str) -> list[str]:
        """
        Return list of cached models for a library.

        Args:
            lib: Library name

        Returns:
            List of model names
        """
        lib_dir = self.get_lib_cache_dir(lib)

        models = []
        for model_dir in lib_dir.iterdir():
            if not model_dir.is_dir():
                continue

            # Check for model files
            if lib == "tokenizers" and (model_dir / "tokenizer.json").exists():
                # Restore original name
                original_name = model_dir.name.replace("--", "/")
                models.append(original_name)
            elif lib == "sentencepiece" and any(model_dir.glob("*.model")):
                original_name = model_dir.name.replace("--", "/")
                models.append(original_name)

        return sorted(models)
    
    def import_local_model(self, lib: str, source_path: Path, model_name: str | None = None) -> str:
        """
        Import local model to LG cache for permanent reuse.

        Args:
            lib: Library name (tokenizers, sentencepiece)
            source_path: Path to local file or directory with model
            model_name: Optional name for model in cache (if None, uses file/directory name)

        Returns:
            Model name in cache (for subsequent use in --encoder)

        Raises:
            FileNotFoundError: If source_path doesn't exist or lacks required files
            ValueError: If model format is unsupported
        """
        import shutil

        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")

        # Determine model name in cache
        if model_name is None:
            # Generate name based on path
            if source_path.is_file():
                # Use filename without extension
                model_name = source_path.stem
            else:
                # Use directory name
                model_name = source_path.name

        # Get cache directory for this model
        cache_dir = self.get_model_cache_dir(lib, model_name)

        if lib == "tokenizers":
            # For tokenizers copy tokenizer.json
            if source_path.is_file() and source_path.suffix == ".json":
                # Direct tokenizer.json file
                dest = cache_dir / "tokenizer.json"
                shutil.copy2(source_path, dest)
                logger.info(f"Imported tokenizer from {source_path} to {dest}")
            elif source_path.is_dir():
                # Directory - look for tokenizer.json inside
                tokenizer_file = source_path / "tokenizer.json"
                if not tokenizer_file.exists():
                    raise FileNotFoundError(f"Directory {source_path} does not contain tokenizer.json")
                dest = cache_dir / "tokenizer.json"
                shutil.copy2(tokenizer_file, dest)
                logger.info(f"Imported tokenizer from {tokenizer_file} to {dest}")
            else:
                raise ValueError(f"Invalid tokenizer source: {source_path} (expected .json file or directory)")

        elif lib == "sentencepiece":
            # For sentencepiece copy .model/.spm file
            if source_path.is_file() and source_path.suffix in [".model", ".spm"]:
                # Direct model file
                dest = cache_dir / source_path.name
                shutil.copy2(source_path, dest)
                logger.info(f"Imported SentencePiece model from {source_path} to {dest}")
            elif source_path.is_dir():
                # Directory - look for .model file inside
                model_files = list(source_path.glob("*.model"))
                if not model_files:
                    model_files = list(source_path.glob("*.spm"))
                if not model_files:
                    raise FileNotFoundError(f"Directory {source_path} does not contain .model or .spm file")
                # Take first found file
                source_file = model_files[0]
                dest = cache_dir / source_file.name
                shutil.copy2(source_file, dest)
                logger.info(f"Imported SentencePiece model from {source_file} to {dest}")
            else:
                raise ValueError(f"Invalid SentencePiece source: {source_path} (expected .model/.spm file or directory)")

        else:
            raise ValueError(f"Unsupported library for import: {lib}")

        return model_name