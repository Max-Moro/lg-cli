import logging
from pathlib import Path

from ...cache.gitignore_helper import ensure_gitignore_entry

logger = logging.getLogger(__name__)

class ModelCache:
    """
    Менеджер кеша загруженных моделей токенизации.
    
    Хранит модели в .lg-cache/tokenizer-models/{lib}/{model_name}/
    """
    
    def __init__(self, root: Path):
        """
        Args:
            root: Корень проекта
        """
        self.root = root
        self.cache_dir = root / ".lg-cache" / "tokenizer-models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Обеспечиваем наличие записи в .gitignore
        ensure_gitignore_entry(root, ".lg-cache/", comment="LG cache directory")
    
    def get_lib_cache_dir(self, lib: str) -> Path:
        """Возвращает директорию для кеша конкретной библиотеки."""
        lib_dir = self.cache_dir / lib
        lib_dir.mkdir(parents=True, exist_ok=True)
        return lib_dir
    
    def get_model_cache_dir(self, lib: str, model_name: str) -> Path:
        """
        Возвращает директорию для кеша конкретной модели.
        
        Args:
            lib: Имя библиотеки (tokenizers, sentencepiece)
            model_name: Имя модели (может содержать /, например google/gemma-2-2b)
        
        Returns:
            Путь к директории кеша модели
        """
        # Безопасное преобразование имени модели в путь
        safe_name = model_name.replace("/", "--")
        model_dir = self.get_lib_cache_dir(lib) / safe_name
        model_dir.mkdir(parents=True, exist_ok=True)
        return model_dir
    
    def is_model_cached(self, lib: str, model_name: str) -> bool:
        """
        Проверяет, закеширована ли модель.
        
        Args:
            lib: Имя библиотеки
            model_name: Имя модели
            
        Returns:
            True если модель есть в кеше
        """
        model_dir = self.get_model_cache_dir(lib, model_name)
        
        # Для tokenizers проверяем наличие tokenizer.json
        if lib == "tokenizers":
            return (model_dir / "tokenizer.json").exists()
        
        # Для sentencepiece проверяем наличие .model файла
        if lib == "sentencepiece":
            return any(model_dir.glob("*.model"))
        
        return False
    
    def list_cached_models(self, lib: str) -> list[str]:
        """
        Возвращает список закешированных моделей для библиотеки.
        
        Args:
            lib: Имя библиотеки
            
        Returns:
            Список имен моделей
        """
        lib_dir = self.get_lib_cache_dir(lib)
        
        models = []
        for model_dir in lib_dir.iterdir():
            if not model_dir.is_dir():
                continue
            
            # Проверяем наличие файлов модели
            if lib == "tokenizers" and (model_dir / "tokenizer.json").exists():
                # Восстанавливаем оригинальное имя
                original_name = model_dir.name.replace("--", "/")
                models.append(original_name)
            elif lib == "sentencepiece" and any(model_dir.glob("*.model")):
                original_name = model_dir.name.replace("--", "/")
                models.append(original_name)
        
        return sorted(models)