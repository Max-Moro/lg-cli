"""
Фикстуры и утилиты для тестов статистики и токенизации.

Предоставляет:
- mock для hf_hub_download (использует предскачанные модели из resources/)
- фикстуры для создания токенизаторов
- хелперы для работы с кешем моделей
"""

import json
import shutil
from pathlib import Path
from typing import Optional

import pytest


# ==================== Пути к ресурсам ====================

@pytest.fixture(scope="session")
def resources_dir() -> Path:
    """Директория с предскачанными моделями для тестов."""
    return Path(__file__).parent / "resources"


@pytest.fixture(scope="session")
def models_manifest(resources_dir: Path) -> dict:
    """
    Манифест с информацией о предскачанных моделях.
    
    Формат:
    {
        "tokenizers": {
            "gpt2": {"filename": "tokenizer.json", "description": "..."},
            ...
        },
        "sentencepiece": {
            "google/gemma-2-2b": {"filename": "tokenizer.model", "description": "..."},
            ...
        }
    }
    """
    manifest_file = resources_dir / "models_manifest.json"
    if not manifest_file.exists():
        return {"tokenizers": {}, "sentencepiece": {}}
    
    with manifest_file.open("r", encoding="utf-8") as f:
        return json.load(f)


# ==================== Mock для HuggingFace Hub ====================

class MockHFHub:
    """Mock для hf_hub_download, использующий локальные ресурсы."""
    
    def __init__(self, resources_dir: Path, manifest: dict):
        self.resources_dir = resources_dir
        self.manifest = manifest
        self.download_count = 0
    
    def download(
        self, 
        repo_id: str, 
        filename: str, 
        cache_dir: Optional[str] = None,
        local_dir: Optional[str] = None,
        local_dir_use_symlinks: bool = False,
        **kwargs
    ) -> str:
        """
        Имитирует hf_hub_download, но возвращает файлы из resources/.
        
        Копирует модель из resources/ в cache_dir для имитации реального поведения.
        """
        self.download_count += 1
        
        # Определяем тип библиотеки по имени файла
        if filename == "tokenizer.json":
            lib_type = "tokenizers"
        elif filename in ("tokenizer.model", "spiece.model", "sentencepiece.model"):
            lib_type = "sentencepiece"
        else:
            raise FileNotFoundError(f"Unknown model file type: {filename}")
        
        # Проверяем наличие модели в манифесте
        models = self.manifest.get(lib_type, {})
        if repo_id not in models:
            raise FileNotFoundError(
                f"Model '{repo_id}' not found in test resources. "
                f"Available models: {list(models.keys())}"
            )
        
        model_info = models[repo_id]
        source_file = self.resources_dir / lib_type / repo_id.replace("/", "--") / model_info["filename"]
        
        if not source_file.exists():
            raise FileNotFoundError(f"Model file not found in resources: {source_file}")
        
        # Копируем в cache_dir (если указан)
        if local_dir:
            target_dir = Path(local_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            shutil.copy2(source_file, target_file)
            return str(target_file)
        elif cache_dir:
            target_dir = Path(cache_dir)
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / filename
            shutil.copy2(source_file, target_file)
            return str(target_file)
        else:
            # Без кеша - просто возвращаем путь к файлу в resources
            return str(source_file)


@pytest.fixture
def mock_hf_hub(resources_dir: Path, models_manifest: dict, monkeypatch):
    """
    Подменяет hf_hub_download на mock, использующий локальные ресурсы.
    
    Использование в тестах:
        def test_something(mock_hf_hub):
            # hf_hub_download теперь использует локальные модели
            adapter = HFAdapter("gpt2", tmp_path)
            ...
            
            # Можно проверить сколько раз скачивалась модель
            assert mock_hf_hub.download_count == 1
    """
    mock = MockHFHub(resources_dir, models_manifest)
    
    # Патчим hf_hub_download в обоих адаптерах
    monkeypatch.setattr(
        "lg.stats.tokenizers.hf_adapter.hf_hub_download",
        mock.download
    )
    monkeypatch.setattr(
        "lg.stats.tokenizers.sp_adapter.hf_hub_download", 
        mock.download
    )
    
    return mock


# ==================== Фикстуры для токенизаторов ====================

@pytest.fixture
def tiktoken_service(tmp_path: Path):
    """Создает TokenService с tiktoken энкодером (дефолтные настройки)."""
    from lg.stats.tokenizer import TokenService
    from tests.infrastructure.cli_utils import DEFAULT_TOKENIZER_LIB, DEFAULT_ENCODER
    
    return TokenService(
        root=tmp_path,
        lib=DEFAULT_TOKENIZER_LIB,
        encoder=DEFAULT_ENCODER
    )


@pytest.fixture
def hf_tokenizer_service(tmp_path: Path, mock_hf_hub):
    """Создает TokenService с HuggingFace токенизатором."""
    from lg.stats.tokenizer import TokenService
    
    return TokenService(
        root=tmp_path,
        lib="tokenizers",
        encoder="gpt2"  # Простая модель для тестов
    )


@pytest.fixture
def sp_tokenizer_service(tmp_path: Path, mock_hf_hub):
    """Создает TokenService с SentencePiece токенизатором."""
    from lg.stats.tokenizer import TokenService
    
    return TokenService(
        root=tmp_path,
        lib="sentencepiece",
        encoder="google/gemma-2-2b"  # Простая модель для тестов
    )


# ==================== Фикстура для тестовых текстов ====================

@pytest.fixture
def sample_texts() -> dict:
    """
    Набор тестовых текстов для сравнения токенизаторов.
    
    Включает:
    - Простой английский текст
    - Код на Python
    - Смешанный контент
    - Специальные символы
    """
    return {
        "simple": "Hello, world! This is a test.",
        "python_code": '''
def hello_world():
    """Prints hello world."""
    print("Hello, world!")
    return 42
'''.strip(),
        "mixed": '''
# Documentation

Here is some Python code:

```python
def process_data(items):
    return [x * 2 for x in items]
```

And some explanation text.
'''.strip(),
        "special_chars": "Special: ñ, ü, 你好, emoji 🚀, symbols @#$%",
        "long_text": " ".join(["This is a longer text with repeated words."] * 50),
    }


# ==================== Утилиты ====================

@pytest.fixture
def clear_model_cache(tmp_path: Path):
    """Очищает кеш моделей перед каждым тестом."""
    cache_dir = tmp_path / ".lg-cache" / "tokenizer-models"
    if cache_dir.exists():
        shutil.rmtree(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir
