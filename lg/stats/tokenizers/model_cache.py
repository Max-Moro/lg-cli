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
    
    def import_local_model(self, lib: str, source_path: Path, model_name: str | None = None) -> str:
        """
        Импортирует локальную модель в кэш LG для постоянного переиспользования.
        
        Args:
            lib: Имя библиотеки (tokenizers, sentencepiece)
            source_path: Путь к локальному файлу или директории с моделью
            model_name: Опциональное имя для модели в кэше (если None, используется имя файла/директории)
            
        Returns:
            Имя модели в кэше (для последующего использования в --encoder)
            
        Raises:
            FileNotFoundError: Если source_path не существует или не содержит нужных файлов
            ValueError: Если формат модели не поддерживается
        """
        import shutil
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source path does not exist: {source_path}")
        
        # Определяем имя модели в кэше
        if model_name is None:
            # Генерируем имя на основе пути
            if source_path.is_file():
                # Используем имя файла без расширения
                model_name = source_path.stem
            else:
                # Используем имя директории
                model_name = source_path.name
        
        # Получаем директорию для кэша этой модели
        cache_dir = self.get_model_cache_dir(lib, model_name)
        
        if lib == "tokenizers":
            # Для tokenizers копируем tokenizer.json
            if source_path.is_file() and source_path.suffix == ".json":
                # Прямой файл tokenizer.json
                dest = cache_dir / "tokenizer.json"
                shutil.copy2(source_path, dest)
                logger.info(f"Imported tokenizer from {source_path} to {dest}")
            elif source_path.is_dir():
                # Директория - ищем tokenizer.json внутри
                tokenizer_file = source_path / "tokenizer.json"
                if not tokenizer_file.exists():
                    raise FileNotFoundError(f"Directory {source_path} does not contain tokenizer.json")
                dest = cache_dir / "tokenizer.json"
                shutil.copy2(tokenizer_file, dest)
                logger.info(f"Imported tokenizer from {tokenizer_file} to {dest}")
            else:
                raise ValueError(f"Invalid tokenizer source: {source_path} (expected .json file or directory)")
        
        elif lib == "sentencepiece":
            # Для sentencepiece копируем .model/.spm файл
            if source_path.is_file() and source_path.suffix in [".model", ".spm"]:
                # Прямой файл модели
                dest = cache_dir / source_path.name
                shutil.copy2(source_path, dest)
                logger.info(f"Imported SentencePiece model from {source_path} to {dest}")
            elif source_path.is_dir():
                # Директория - ищем .model файл внутри
                model_files = list(source_path.glob("*.model"))
                if not model_files:
                    model_files = list(source_path.glob("*.spm"))
                if not model_files:
                    raise FileNotFoundError(f"Directory {source_path} does not contain .model or .spm file")
                # Берем первый найденный файл
                source_file = model_files[0]
                dest = cache_dir / source_file.name
                shutil.copy2(source_file, dest)
                logger.info(f"Imported SentencePiece model from {source_file} to {dest}")
            else:
                raise ValueError(f"Invalid SentencePiece source: {source_path} (expected .model/.spm file or directory)")
        
        else:
            raise ValueError(f"Unsupported library for import: {lib}")
        
        return model_name