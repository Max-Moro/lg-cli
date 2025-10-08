# Техническое задание: Переработка подсистемы токенизации и статистики в LG

## 1. Бизнес-требования

### Проблемы текущей реализации

1. **Устаревание конфигурации**: `lg-cfg/models.yaml` с хардкод-списком моделей и планов быстро устаревает из-за активного развития индустрии LLM.

2. **Ограниченная совместимость**: Привязка к `tiktoken` (OpenAI) не позволяет корректно работать с токенизаторами других провайдеров (Anthropic, Google, xAI).

3. **Сложная логика лимитов**: Вычисление эффективного контекстного окна через "планы провайдеров" избыточно и трудно актуализируемо.

### Целевое решение

**Явный API для токенизации**: пользователь самостоятельно указывает библиотеку, энкодер и размер контекстного окна через CLI-аргументы при каждом запуске. Это обеспечивает:

- **Прозрачность**: нет скрытой магии, все параметры явные
- **Гибкость**: поддержка множества библиотек токенизации
- **Актуальность**: не требуется обновление LG при появлении новых моделей
- **Универсальность**: работа с любыми провайдерами через опенсорсные токенизаторы

### Контекст использования

LG используется исключительно через IDE-аддоны (VS Code, JetBrains), которые имеют:
- Развитый UI для управления настройками
- Систему профилей и сохранения состояния
- Возможность частого переключения параметров без редактирования YAML

Поэтому verbose CLI (3 обязательных параметра вместо 1) не является проблемой для UX.

---

## 2. Технические требования

### 2.1. Поддерживаемые библиотеки токенизации

Интегрируем три опенсорсные библиотеки:

1. **`tiktoken`** (OpenAI) - GPT-модели, быстрый C-адаптер
2. **`tokenizers`** (HuggingFace) - универсальная Rust-библиотека с множеством алгоритмов
3. **`sentencepiece`** (Google) - используется в Gemini и многих открытых моделях

**Обоснование**: эти библиотеки покрывают >90% популярных моделей. Для закрытых токенизаторов (Claude, Grok) используется approximation через похожие алгоритмы.

### 2.2. Новое CLI

#### Удаляемые команды

```bash
# УДАЛИТЬ
lg report ctx:all --model gpt-4o
lg list models
```

#### Новые команды

```bash
# Список библиотек
lg list tokenizer-libs
# → ["tiktoken", "tokenizers", "sentencepiece"]

# Список энкодеров для библиотеки
lg list encoders --lib tiktoken
lg list encoders --lib tokenizers
lg list encoders --lib sentencepiece

# Рендеринг/отчет с явными параметрами (все 3 обязательны)
lg render ctx:all --lib tiktoken --encoder cl100k_base --ctx-limit 128000
lg report sec:core --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 1000000
```

### 2.3. Кеширование моделей

- **Директория**: `lg-cfg/tokenizer-models/` (внутри репозитория, игнорируется git)
- **Структура**: `lg-cfg/tokenizer-models/{lib}/{model_name}/`
- **Автозагрузка**: при первом использовании модели скачиваются с HuggingFace Hub
- **Отдельный модуль**: `lg/stats/model_cache.py` (не смешивать с `lg/cache/fs_cache.py`)

### 2.4. Обработка энкодеров

#### `tiktoken`
- Встроенные энкодеры: `gpt2`, `r50k_base`, `p50k_base`, `cl100k_base`, `o200k_base`
- Список через встроенный API: `tiktoken.list_encoding_names()`
- Не требуют скачивания

#### `tokenizers` (HuggingFace)
- Рекомендуемые модели (хардкод-список): `gpt2`, `roberta-base`, `bert-base-uncased`, `bert-base-cased`, `t5-base`, `google/gemma-tokenizer`
- Поддержка любых моделей с HF Hub через `Tokenizer.from_pretrained(model_name)`
- Кеширование в `lg-cfg/tokenizer-models/tokenizers/{model_name}/`

#### `sentencepiece`
- Рекомендуемые модели (хардкод-список): `google/gemma-2-2b`, `meta-llama/Llama-2-7b-hf`
- Поддержка локальных `.spm` файлов: `--encoder /path/to/model.spm`
- Поддержка любых моделей с HF Hub
- Кеширование в `lg-cfg/tokenizer-models/sentencepiece/{model_name}/`

### 2.5. JSON схема отчета (protocol v5)

```json
{
  "protocol": 5,
  "tokenizerLib": "tiktoken",
  "encoder": "o200k_base",
  "ctxLimit": 200000,
  "scope": "context",
  "target": "ctx:all",
  "total": { ... },
  "files": [ ... ],
  "context": { ... }
}
```

**Изменения**:
- `protocol`: 4 → 5
- **УДАЛЕНО**: поле `model`
- **ДОБАВЛЕНО**: `tokenizerLib` (строка: `tiktoken|tokenizers|sentencepiece`)
- **СОХРАНЕНО**: `encoder`, `ctxLimit`

---

## 3. Архитектура решения

### 3.1. Структура модуля `lg/stats/`

#### Удаляемые файлы

```
lg/stats/
├── load.py          ❌ УДАЛИТЬ ПОЛНОСТЬЮ
├── model.py         ❌ УДАЛИТЬ ПОЛНОСТЬЮ
```

#### Новая структура

```
lg/stats/
├── __init__.py                      ⚙️ Обновить экспорты
├── collector.py                     ✅ Без изменений
├── report_builder.py                📝 Упростить (убрать логику планов)
├── report_schema.py                 📝 Обновить Pydantic-модели
├── tokenizers/                      ⭐ НОВЫЙ ПОДМОДУЛЬ
│   ├── __init__.py                  - Фабрика и публичный API
│   ├── base.py                      - Абстрактный класс BaseTokenizer
│   ├── tiktoken_adapter.py          - Адаптер для tiktoken
│   ├── hf_adapter.py                - Адаптер для HuggingFace tokenizers
│   ├── sp_adapter.py                - Адаптер для SentencePiece
│   └── model_cache.py               - Менеджер кеша моделей
```

### 3.2. Обновление зависимостей

```toml
# pyproject.toml

[project]
dependencies = [
    "ruamel.yaml>=0.18",
    "pathspec>=0.12",
    "tiktoken>=0.6",
    "tokenizers>=0.15",           # ⭐ НОВОЕ
    "sentencepiece>=0.2",         # ⭐ НОВОЕ
    "huggingface-hub>=0.20",      # ⭐ НОВОЕ (для автозагрузки)
    "pydantic>=2.0,<3.0",
    "tree-sitter>=0.21",
    # ...
]
```

### 3.3. Обновление CLI

```python
# lg/cli.py

# УДАЛИТЬ опцию --model из всех команд
# ДОБАВИТЬ новые опции для render/report:
#   --lib <tiktoken|tokenizers|sentencepiece>
#   --encoder <encoder_name>
#   --ctx-limit <int>

# УДАЛИТЬ подкоманду lg list models

# ДОБАВИТЬ новые подкоманды:
#   lg list tokenizer-libs
#   lg list encoders --lib <lib_name>
```

---

## 4. Детальная реализация

### 4.1. Абстрактный базовый класс

**Файл**: `lg/stats/tokenizers/base.py`

```python
from abc import ABC, abstractmethod
from typing import List

class BaseTokenizer(ABC):
    """
    Абстрактный базовый класс для всех токенизаторов.
    
    Унифицирует интерфейс работы с разными библиотеками токенизации.
    """
    
    def __init__(self, encoder: str, ctx_limit: int):
        """
        Args:
            encoder: Имя энкодера (для tiktoken) или модели (для HF/SP)
            ctx_limit: Размер контекстного окна в токенах
        """
        self.encoder = encoder
        self.ctx_limit = ctx_limit
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Подсчитывает количество токенов в тексте.
        
        Args:
            text: Исходный текст
            
        Returns:
            Количество токенов
        """
        pass
    
    @abstractmethod
    def encode(self, text: str) -> List[int]:
        """
        Кодирует текст в список token IDs.
        
        Args:
            text: Исходный текст
            
        Returns:
            Список token IDs
        """
        pass
    
    @abstractmethod
    def decode(self, token_ids: List[int]) -> str:
        """
        Декодирует token IDs обратно в текст.
        
        Args:
            token_ids: Список token IDs
            
        Returns:
            Декодированный текст
        """
        pass
    
    @staticmethod
    @abstractmethod
    def list_available_encoders() -> List[str]:
        """
        Возвращает список доступных энкодеров для данной библиотеки.
        
        Включает:
        - Встроенные энкодеры (для tiktoken)
        - Рекомендуемые модели (для HF/SP)
        - Уже скачанные модели
        
        Returns:
            Список имен энкодеров/моделей
        """
        pass
    
    @property
    def lib_name(self) -> str:
        """Имя библиотеки токенизации (tiktoken, tokenizers, sentencepiece)."""
        return self.__class__.__name__.replace("Adapter", "").lower()
    
    @property
    def full_name(self) -> str:
        """Полное имя токенизатора в формате 'lib:encoder'."""
        return f"{self.lib_name}:{self.encoder}"
```

---

### 4.2. Менеджер кеша моделей

**Файл**: `lg/stats/tokenizers/model_cache.py`

```python
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class ModelCache:
    """
    Менеджер кеша загруженных моделей токенизации.
    
    Хранит модели в lg-cfg/tokenizer-models/{lib}/{model_name}/
    """
    
    def __init__(self, root: Path):
        """
        Args:
            root: Корень проекта (где находится lg-cfg/)
        """
        self.root = root
        self.cache_dir = root / "lg-cfg" / "tokenizer-models"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Добавляем в .gitignore если его нет
        self._ensure_gitignore()
    
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
    
    def _ensure_gitignore(self) -> None:
        """Добавляет tokenizer-models/ в lg-cfg/.gitignore если нужно."""
        gitignore_path = self.cache_dir.parent / ".gitignore"
        entry = "tokenizer-models/\n"
        
        if gitignore_path.exists():
            content = gitignore_path.read_text(encoding="utf-8")
            if "tokenizer-models" not in content:
                gitignore_path.write_text(content + entry, encoding="utf-8")
        else:
            gitignore_path.write_text(entry, encoding="utf-8")
```

---

### 4.3. Адаптер для tiktoken

**Файл**: `lg/stats/tokenizers/tiktoken_adapter.py`

```python
import tiktoken
from typing import List
from .base import BaseTokenizer

class TiktokenAdapter(BaseTokenizer):
    """Адаптер для библиотеки tiktoken (OpenAI)."""
    
    def __init__(self, encoder: str, ctx_limit: int):
        super().__init__(encoder, ctx_limit)
        
        try:
            self._enc = tiktoken.get_encoding(encoder)
        except Exception as e:
            available = tiktoken.list_encoding_names()
            raise ValueError(
                f"Unknown tiktoken encoding '{encoder}'. "
                f"Available: {', '.join(available)}"
            ) from e
    
    def count_tokens(self, text: str) -> int:
        if not text:
            return 0
        return len(self._enc.encode(text))
    
    def encode(self, text: str) -> List[int]:
        return self._enc.encode(text)
    
    def decode(self, token_ids: List[int]) -> str:
        return self._enc.decode(token_ids)
    
    @staticmethod
    def list_available_encoders() -> List[str]:
        """Возвращает список встроенных энкодеров tiktoken."""
        return tiktoken.list_encoding_names()
```

---

### 4.4. Адаптер для HuggingFace tokenizers

**Файл**: `lg/stats/tokenizers/hf_adapter.py`

```python
from pathlib import Path
from typing import List
import logging

from tokenizers import Tokenizer
from huggingface_hub import hf_hub_download

from .base import BaseTokenizer
from .model_cache import ModelCache

logger = logging.getLogger(__name__)

# Рекомендуемые универсальные токенизаторы (не привязаны к продуктовым LLM)
RECOMMENDED_TOKENIZERS = [
    "gpt2",                    # GPT-2 BPE
    "roberta-base",            # RoBERTa BPE
    "bert-base-uncased",       # BERT WordPiece
    "bert-base-cased",         # BERT WordPiece (case-sensitive)
    "t5-base",                 # T5 SentencePiece-based
    "google/gemma-tokenizer",  # Gemma (Google)
]

class HFAdapter(BaseTokenizer):
    """Адаптер для библиотеки tokenizers (HuggingFace)."""
    
    def __init__(self, encoder: str, ctx_limit: int, root: Path):
        super().__init__(encoder, ctx_limit)
        self.root = root
        self.model_cache = ModelCache(root)
        
        # Загружаем токенизатор
        self._tokenizer = self._load_tokenizer(encoder)
    
    def _load_tokenizer(self, model_name: str) -> Tokenizer:
        """
        Загружает токенизатор из кеша или HuggingFace Hub.
        
        Args:
            model_name: Имя модели на HF или локальный путь
            
        Returns:
            Загруженный токенизатор
        """
        # Проверяем кеш
        if self.model_cache.is_model_cached("tokenizers", model_name):
            cache_dir = self.model_cache.get_model_cache_dir("tokenizers", model_name)
            tokenizer_path = cache_dir / "tokenizer.json"
            logger.info(f"Loading tokenizer from cache: {tokenizer_path}")
            return Tokenizer.from_file(str(tokenizer_path))
        
        # Скачиваем с HuggingFace Hub
        logger.info(f"Downloading tokenizer '{model_name}' from HuggingFace Hub...")
        try:
            cache_dir = self.model_cache.get_model_cache_dir("tokenizers", model_name)
            
            # Скачиваем tokenizer.json
            tokenizer_file = hf_hub_download(
                repo_id=model_name,
                filename="tokenizer.json",
                cache_dir=str(cache_dir),
                local_dir=str(cache_dir),
                local_dir_use_symlinks=False,
            )
            
            tokenizer = Tokenizer.from_file(tokenizer_file)
            logger.info(f"Tokenizer '{model_name}' downloaded and cached successfully")
            return tokenizer
        
        except Exception as e:
            raise RuntimeError(
                f"Failed to load tokenizer '{model_name}' from HuggingFace Hub. "
                f"Ensure the model name is correct and you have internet connection."
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
    def list_available_encoders(root: Path) -> List[str]:
        """
        Возвращает список доступных токенизаторов.
        
        Включает:
        - Рекомендуемые модели
        - Уже скачанные модели
        
        Args:
            root: Корень проекта
            
        Returns:
            Список имен моделей
        """
        model_cache = ModelCache(root)
        cached = model_cache.list_cached_models("tokenizers")
        
        # Объединяем рекомендуемые и кешированные (без дубликатов)
        all_models = list(RECOMMENDED_TOKENIZERS)
        for cached_model in cached:
            if cached_model not in all_models:
                all_models.append(cached_model)
        
        return all_models
```

---

### 4.5. Адаптер для SentencePiece

**Файл**: `lg/stats/tokenizers/sp_adapter.py`

```python
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
    
    def __init__(self, encoder: str, ctx_limit: int, root: Path):
        super().__init__(encoder, ctx_limit)
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
    def list_available_encoders(root: Path) -> List[str]:
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
```

---

### 4.6. Фабрика и публичный API

**Файл**: `lg/stats/tokenizers/__init__.py`

```python
from pathlib import Path
from typing import List

from .base import BaseTokenizer
from .tiktoken_adapter import TiktokenAdapter
from .hf_adapter import HFAdapter
from .sp_adapter import SPAdapter

def create_tokenizer(lib: str, encoder: str, ctx_limit: int, root: Path) -> BaseTokenizer:
    """
    Создает токенизатор по параметрам.
    
    Args:
        lib: Имя библиотеки (tiktoken, tokenizers, sentencepiece)
        encoder: Имя энкодера/модели
        ctx_limit: Размер контекстного окна в токенах
        root: Корень проекта
        
    Returns:
        Инстанс токенизатора
        
    Raises:
        ValueError: Если библиотека неизвестна
    """
    if lib == "tiktoken":
        return TiktokenAdapter(encoder, ctx_limit)
    elif lib == "tokenizers":
        return HFAdapter(encoder, ctx_limit, root)
    elif lib == "sentencepiece":
        return SPAdapter(encoder, ctx_limit, root)
    else:
        raise ValueError(
            f"Unknown tokenizer library: '{lib}'. "
            f"Supported: tiktoken, tokenizers, sentencepiece"
        )

def list_tokenizer_libs() -> List[str]:
    """Возвращает список поддерживаемых библиотек токенизации."""
    return ["tiktoken", "tokenizers", "sentencepiece"]

def list_encoders(lib: str, root: Path) -> List[str]:
    """
    Возвращает список доступных энкодеров для библиотеки.
    
    Args:
        lib: Имя библиотеки
        root: Корень проекта (для доступа к кешу)
        
    Returns:
        Список имен энкодеров/моделей
        
    Raises:
        ValueError: Если библиотека неизвестна
    """
    if lib == "tiktoken":
        return TiktokenAdapter.list_available_encoders()
    elif lib == "tokenizers":
        return HFAdapter.list_available_encoders(root)
    elif lib == "sentencepiece":
        return SPAdapter.list_available_encoders(root)
    else:
        raise ValueError(
            f"Unknown tokenizer library: '{lib}'. "
            f"Supported: tiktoken, tokenizers, sentencepiece"
        )

__all__ = [
    "BaseTokenizer",
    "create_tokenizer",
    "list_tokenizer_libs",
    "list_encoders",
]
```

---

### 4.7. Обновление lg/stats/__init__.py

**Файл**: `lg/stats/__init__.py`

```python
# Удаляем старые экспорты
# from .load import load_models, list_models, get_model_info  ❌ УДАЛИТЬ
# from .model import ModelInfo, ModelsConfig, PlanInfo, ResolvedModel  ❌ УДАЛИТЬ

# Добавляем новые экспорты
from .tokenizers import (
    BaseTokenizer,
    create_tokenizer,
    list_tokenizer_libs,
    list_encoders,
)

# Оставляем существующие экспорты
from .collector import StatsCollector
from .report_builder import build_run_result_from_collector
from .report_schema import RunResult, Total, File, Context, Scope

__all__ = [
    # Tokenizers
    "BaseTokenizer",
    "create_tokenizer",
    "list_tokenizer_libs",
    "list_encoders",
    
    # Stats
    "StatsCollector",
    "build_run_result_from_collector",
    
    # Report schema
    "RunResult",
    "Total",
    "File",
    "Context",
    "Scope",
]
```

---

### 4.8. Обновление JSON схемы отчета

**Файл**: `lg/stats/report_schema.py`

**Изменения**:

```python
# БЫЛО (protocol 4)
class RunResult(BaseModel):
    protocol: conint(ge=1)
    scope: Scope
    target: str
    model: str              # ❌ УДАЛИТЬ
    encoder: str
    ctxLimit: conint(ge=1)
    # ...

# СТАЛО (protocol 5)
class RunResult(BaseModel):
    protocol: conint(ge=1)
    scope: Scope
    target: str
    tokenizerLib: str       # ⭐ НОВОЕ: tiktoken|tokenizers|sentencepiece
    encoder: str
    ctxLimit: conint(ge=1)
    # ...
```

**Полный обновленный файл**:

```python
# generated by datamodel-codegen:
#   filename:  report.schema.json

from __future__ import annotations

from enum import Enum
from typing import Optional, Union

from pydantic import BaseModel, ConfigDict, conint


class Scope(Enum):
    context = 'context'
    section = 'section'


class Total(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    sizeBytes: conint(ge=0)
    tokensProcessed: conint(ge=0)
    tokensRaw: conint(ge=0)
    savedTokens: conint(ge=0)
    savedPct: float
    ctxShare: float
    renderedTokens: Optional[conint(ge=0)] = None
    renderedOverheadTokens: Optional[conint(ge=0)] = None
    metaSummary: dict[str, int]


class File(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    path: str
    sizeBytes: conint(ge=0)
    tokensRaw: conint(ge=0)
    tokensProcessed: conint(ge=0)
    savedTokens: conint(ge=0)
    savedPct: float
    promptShare: float
    ctxShare: float
    meta: dict[str, Union[str, int, float, bool]]


class Context(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    templateName: str
    sectionsUsed: dict[str, conint(ge=1)]
    finalRenderedTokens: Optional[conint(ge=0)] = None
    templateOnlyTokens: Optional[conint(ge=0)] = None
    templateOverheadPct: Optional[float] = None
    finalCtxShare: Optional[float] = None


class RunResult(BaseModel):
    model_config = ConfigDict(
        extra='forbid',
    )
    protocol: conint(ge=1)
    scope: Scope
    target: str
    tokenizerLib: str  # ⭐ НОВОЕ: tiktoken|tokenizers|sentencepiece
    encoder: str
    ctxLimit: conint(ge=1)
    total: Total
    files: list[File]
    context: Optional[Context] = None
```

---

### 4.9. Обновление lg/stats/collector.py

**Минимальные изменения**: заменить использование `TokenService.model_info` на прямой доступ к параметрам токенизатора.

**Патч**:

```python
# БЫЛО
model_info = self.tokenizer.model_info
prompt_share = (file_stats.tokens_processed / model_info.ctx_limit * 100.0) if model_info.ctx_limit else 0.0

# СТАЛО
ctx_limit = self.tokenizer.ctx_limit
prompt_share = (file_stats.tokens_processed / ctx_limit * 100.0) if ctx_limit else 0.0
```

**Аналогично** для всех мест, где используется `model_info.ctx_limit` - заменить на `self.tokenizer.ctx_limit`.

---

### 4.10. Переработка lg/stats/tokenizer.py

**Старая реализация** (`TokenService`) сложная и привязана к `models.yaml`. 

**Новая реализация**: тонкая обёртка над `BaseTokenizer` с кешированием.

**Файл**: `lg/stats/tokenizer.py`

```python
from __future__ import annotations

from pathlib import Path
from typing import Tuple, Optional

from .tokenizers import BaseTokenizer, create_tokenizer

"""
Сервис подсчёта токенов (упрощенная версия).

Создаётся один раз на старте пайплайна и предоставляет
унифицированное API для работы с разными токенизаторами.
"""

class TokenService:
    """
    Обёртка над BaseTokenizer с встроенным кешированием.
    """

    def __init__(
        self,
        root: Path,
        lib: str,
        encoder: str,
        ctx_limit: int,
        *,
        cache=None
    ):
        """
        Args:
            root: Корень проекта
            lib: Имя библиотеки (tiktoken, tokenizers, sentencepiece)
            encoder: Имя энкодера/модели
            ctx_limit: Размер контекстного окна в токенах
            cache: Кеш для токенов (опционально)
        """
        self.root = root
        self.lib = lib
        self.encoder = encoder
        self.ctx_limit = ctx_limit
        self.cache = cache
        
        # Создаем токенизатор
        self._tokenizer = create_tokenizer(lib, encoder, ctx_limit, root)

    @property
    def tokenizer(self) -> BaseTokenizer:
        """Возвращает базовый токенизатор."""
        return self._tokenizer

    @property
    def encoder_name(self) -> str:
        """Имя энкодера."""
        return self.encoder

    def count_text(self, text: str) -> int:
        """Подсчитать токены в тексте."""
        return self._tokenizer.count_tokens(text)
    
    def count_text_cached(self, text: str) -> int:
        """
        Подсчитать токены в тексте с использованием кеша.
        
        Args:
            text: Текст для подсчета токенов
            
        Returns:
            Количество токенов
        """
        if not text:
            return 0
        
        # Если нет кеша, просто считаем
        if not self.cache:
            return self.count_text(text)
        
        # Пытаемся получить из кеша
        # Ключ: lib:encoder
        cache_key = f"{self.lib}:{self.encoder}"
        cached_tokens = self.cache.get_text_tokens(text, cache_key)
        if cached_tokens is not None:
            return cached_tokens
        
        # Если нет в кеше, подсчитываем и сохраняем
        token_count = self.count_text(text)
        self.cache.put_text_tokens(text, cache_key, token_count)
        
        return token_count

    def compare_texts(self, original: str, replacement: str) -> Tuple[int, int, int, float]:
        """
        Сравнить стоимость оригинала и замены.

        Returns: (orig_tokens, repl_tokens, savings, ratio)
        ratio = savings / max(repl_tokens, 1)
        """
        orig = self.count_text(original)
        repl = self.count_text(replacement)
        savings = max(0, orig - repl)
        ratio = savings / float(max(repl, 1))
        return orig, repl, savings, ratio

    def is_economical(
        self, 
        original: str, 
        replacement: str, 
        *, 
        min_ratio: float, 
        replacement_is_none: bool,
        min_abs_savings_if_none: int
    ) -> bool:
        """
        Проверка целесообразности замены.

        - Для обычных плейсхолдеров применяется только порог отношения savings/replacement ≥ min_ratio.
        - Для "пустых" замен (replacement_is_none=True) дополнительно может применяться абсолютный порог
          экономии токенов (min_abs_savings_if_none), чтобы избежать микроскопических удалений.
        """
        orig, repl, savings, ratio = self.compare_texts(original, replacement)

        if replacement_is_none and savings < min_abs_savings_if_none:
            return False

        return ratio >= float(min_ratio)

    def truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """
        Урезает текст до указанного количества токенов используя пропорциональное отношение.
        
        Args:
            text: Исходный текст для урезания
            max_tokens: Максимальное количество токенов
            
        Returns:
            Урезанный текст, который помещается в указанный лимит токенов
        """
        if not text:
            return ""
        
        current_tokens = self.count_text(text)
        if current_tokens <= max_tokens:
            return text
        
        # Пропорциональное урезание по символам
        ratio = max_tokens / current_tokens
        target_length = int(len(text) * ratio)
        
        # Урезаем до целевой длины, но не меньше 1 символа
        target_length = max(1, target_length)
        trimmed = text[:target_length].rstrip()
        
        return trimmed
```

---

### 4.11. Обновление lg/run_context.py

**Патч**: заменить создание `TokenService`.

```python
# БЫЛО
self.tokenizer = TokenService(self.root, self.options.model, cache=self.cache)

# СТАЛО
self.tokenizer = TokenService(
    root=self.root,
    lib=self.options.tokenizer_lib,
    encoder=self.options.encoder,
    ctx_limit=self.options.ctx_limit,
    cache=self.cache
)
```

---

### 4.12. Обновление lg/types.py

**Патч**: обновить `RunOptions`.

```python
@dataclass(frozen=True)
class RunOptions:
    # ❌ УДАЛИТЬ
    # model: ModelName = ModelName("o3")
    
    # ⭐ НОВОЕ: параметры токенизации
    tokenizer_lib: str = "tiktoken"
    encoder: str = "cl100k_base"
    ctx_limit: int = 128000
    
    # Адаптивные возможности (без изменений)
    modes: Dict[str, str] = field(default_factory=dict)
    extra_tags: Set[str] = field(default_factory=set)
    task_text: Optional[str] = None
    target_branch: Optional[str] = None
```

---

### 4.13. Обновление lg/cli.py

**Большой патч**: обновить аргументы команд и добавить новые подкоманды.

#### Удалить --model из render/report

```python
def add_common(sp: argparse.ArgumentParser) -> None:
    sp.add_argument(
        "target",
        help="ctx:<name> | sec:<name> | <name> (сначала ищется контекст, иначе секция)",
    )
    
    # ❌ УДАЛИТЬ
    # sp.add_argument("--model", default="o3", help="базовая модель для статистики")
    
    # ⭐ НОВОЕ: явные параметры токенизации
    sp.add_argument(
        "--lib",
        required=True,
        choices=["tiktoken", "tokenizers", "sentencepiece"],
        help="библиотека токенизации"
    )
    sp.add_argument(
        "--encoder",
        required=True,
        help="имя энкодера/модели"
    )
    sp.add_argument(
        "--ctx-limit",
        type=int,
        required=True,
        help="размер контекстного окна в токенах"
    )
    
    # Остальные аргументы без изменений
    sp.add_argument("--mode", action="append", metavar="MODESET:MODE", ...)
    sp.add_argument("--tags", help="дополнительные теги через запятую")
    sp.add_argument("--task", metavar="TEXT|@FILE|-", help=...)
    sp.add_argument("--target-branch", metavar="BRANCH", help=...)
```

#### Обновить _opts()

```python
def _opts(ns: argparse.Namespace) -> RunOptions:
    modes = _parse_modes(getattr(ns, "mode", None))
    extra_tags = _parse_tags(getattr(ns, "tags", None))
    task_text = _parse_task(getattr(ns, "task", None))
    target_branch = getattr(ns, "target_branch", None)
    
    return RunOptions(
        tokenizer_lib=ns.lib,
        encoder=ns.encoder,
        ctx_limit=ns.ctx_limit,
        modes=modes,
        extra_tags=extra_tags,
        task_text=task_text,
        target_branch=target_branch,
    )
```

#### Удалить подкоманду list models

```python
# ❌ УДАЛИТЬ ЦЕЛЫЙ БЛОК
# if ns.what == "models":
#     from .stats import list_models
#     data = {"models": list_models(root)}
```

#### Добавить новые подкоманды

```python
# В sp_list (после "tag-sets")
sp_list = sub.add_parser("list", help="Списки сущностей (JSON)")
sp_list.add_argument(
    "what",
    choices=[
        "contexts",
        "sections",
        "mode-sets",
        "tag-sets",
        "tokenizer-libs",  # ⭐ НОВОЕ
        "encoders"         # ⭐ НОВОЕ
    ],
    help="что вывести"
)

# Для encoders нужен --lib
sp_list.add_argument(
    "--lib",
    choices=["tiktoken", "tokenizers", "sentencepiece"],
    help="библиотека для списка энкодеров (требуется для what=encoders)"
)

# В main() добавить обработку
if ns.what == "tokenizer-libs":
    from .stats import list_tokenizer_libs
    data = {"tokenizer_libs": list_tokenizer_libs()}

elif ns.what == "encoders":
    if not ns.lib:
        sys.stderr.write("Error: --lib is required for 'encoders'\n")
        return 2
    from .stats import list_encoders
    root = Path.cwd()
    data = {"lib": ns.lib, "encoders": list_encoders(ns.lib, root)}
```

---

### 4.14. Обновление lg/stats/report_builder.py

**Патч**: упростить генерацию отчета (убрать логику планов).

```python
def build_run_result_from_collector(
    collector: StatsCollector,
    target_spec: TargetSpec
) -> RunResult:
    """
    Строит RunResult из собранной коллектором статистики.
    """
    files_rows, totals, ctx_block = collector.compute_final_stats()
    
    # ❌ УДАЛИТЬ
    # model_info = collector.tokenizer.model_info
    
    # ⭐ НОВОЕ: берем параметры напрямую
    tokenizer = collector.tokenizer
    
    # Мэппинг Totals в Total
    total = Total(
        sizeBytes=totals.sizeBytes,
        tokensProcessed=totals.tokensProcessed,
        tokensRaw=totals.tokensRaw,
        savedTokens=totals.savedTokens,
        savedPct=totals.savedPct,
        ctxShare=totals.ctxShare,
        renderedTokens=totals.renderedTokens,
        renderedOverheadTokens=totals.renderedOverheadTokens,
        metaSummary=dict(totals.metaSummary or {}),
    )

    # Мэппинг файлов
    files = [
        File(
            path=row.path,
            sizeBytes=row.sizeBytes,
            tokensRaw=row.tokensRaw,
            tokensProcessed=row.tokensProcessed,
            savedTokens=row.savedTokens,
            savedPct=row.savedPct,
            promptShare=row.promptShare,
            ctxShare=row.ctxShare,
            meta=dict(row.meta or {}),
        )
        for row in files_rows
    ]

    # Scope и target
    scope = Scope.context if target_spec.kind == "context" else Scope.section
    target_norm = f"{'ctx' if target_spec.kind == 'context' else 'sec'}:{target_spec.name}"

    # Контекстный блок
    context: Context | None = None
    if scope is Scope.context:
        context = Context(
            templateName=ctx_block.templateName,
            sectionsUsed=dict(ctx_block.sectionsUsed),
            finalRenderedTokens=ctx_block.finalRenderedTokens,
            templateOnlyTokens=ctx_block.templateOnlyTokens,
            templateOverheadPct=ctx_block.templateOverheadPct,
            finalCtxShare=ctx_block.finalCtxShare,
        )

    # ⭐ НОВОЕ: protocol 5 с новыми полями
    result = RunResult(
        protocol=5,  # Bump версии
        scope=scope,
        target=target_norm,
        tokenizerLib=tokenizer.lib,
        encoder=tokenizer.encoder,
        ctxLimit=tokenizer.ctx_limit,
        total=total,
        files=files,
        context=context,
    )
    
    return result
```

---

### 4.15. Обновление lg/protocol.py

**Файл**: `lg/protocol.py`

```python
# БЫЛО
PROTOCOL_VERSION = 4

# СТАЛО
PROTOCOL_VERSION = 5
```

---

### 4.16. Обновление pyproject.toml

**Файл**: `pyproject.toml`

```toml
[project]
dependencies = [
    "ruamel.yaml>=0.18",
    "pathspec>=0.12",
    "tiktoken>=0.6",
    "tokenizers>=0.15",         # ⭐ НОВОЕ
    "sentencepiece>=0.2",       # ⭐ НОВОЕ
    "huggingface-hub>=0.20",    # ⭐ НОВОЕ
    "pydantic>=2.0,<3.0",
    "tree-sitter>=0.21",
    "tree-sitter-python>=0.23",
    "tree-sitter-typescript>=0.23",
    "tree-sitter-javascript>=0.25",
]
```

---

## 5. Миграция пользовательских данных

### 5.1. Что удалить через миграцию

**Удаляемые файлы из lg-cfg/**:
- `models.yaml` - полностью устаревший формат

### 5.2. Что добавить через миграцию

**Новые записи в .gitignore**:
```gitignore
# lg-cfg/.gitignore
tokenizer-models/
```

### 5.3. Скрипт миграции

**Файл**: `lg/migrate/migrations/m006_remove_models_yaml.py`

```python
"""
M006: Удаление устаревшего models.yaml.

Удаляет lg-cfg/models.yaml, так как новая версия LG использует
явные параметры токенизации через CLI.
"""

from pathlib import Path
from typing import List

from ..errors import MigrationError
from ..model import Migration


def migrate(cfg_root: Path) -> List[str]:
    """
    Удаляет models.yaml и добавляет tokenizer-models/ в .gitignore.
    
    Args:
        cfg_root: Путь к lg-cfg/
        
    Returns:
        Список сообщений о выполненных действиях
    """
    actions = []
    
    # Удаляем models.yaml если существует
    models_path = cfg_root / "models.yaml"
    if models_path.exists():
        models_path.unlink()
        actions.append("Removed obsolete models.yaml")
    
    # Добавляем tokenizer-models/ в .gitignore
    gitignore_path = cfg_root / ".gitignore"
    entry = "tokenizer-models/\n"
    
    if gitignore_path.exists():
        content = gitignore_path.read_text(encoding="utf-8")
        if "tokenizer-models" not in content:
            gitignore_path.write_text(content + entry, encoding="utf-8")
            actions.append("Added tokenizer-models/ to .gitignore")
    else:
        gitignore_path.write_text(entry, encoding="utf-8")
        actions.append("Created .gitignore with tokenizer-models/")
    
    return actions


# Регистрация миграции
M006 = Migration(
    id="m006_remove_models_yaml",
    description="Remove obsolete models.yaml and prepare for new tokenization system",
    apply=migrate,
)
```

**Регистрация в списке миграций**:

```python
# lg/migrate/registry.py

from .migrations.m006_remove_models_yaml import M006

MIGRATIONS = [
    # ... существующие миграции ...
    M006,
]
```

---

## 6. Тестирование

### 6.1. Ручное тестирование

```bash
# 1. Список библиотек
lg list tokenizer-libs
# Expected: ["tiktoken", "tokenizers", "sentencepiece"]

# 2. Список энкодеров для tiktoken
lg list encoders --lib tiktoken
# Expected: ["gpt2", "r50k_base", "p50k_base", "cl100k_base", "o200k_base"]

# 3. Список энкодеров для tokenizers (первый запуск - только рекомендуемые)
lg list encoders --lib tokenizers
# Expected: ["gpt2", "roberta-base", "bert-base-uncased", ...]

# 4. Рендеринг с tiktoken
lg render ctx:all --lib tiktoken --encoder cl100k_base --ctx-limit 128000

# 5. Отчет с tokenizers (автозагрузка модели)
lg report sec:core --lib tokenizers --encoder gpt2 --ctx-limit 50000 > report.json

# 6. Проверка JSON схемы
cat report.json | jq '.protocol, .tokenizerLib, .encoder, .ctxLimit'
# Expected: 5, "tokenizers", "gpt2", 50000

# 7. Список энкодеров после скачивания
lg list encoders --lib tokenizers
# Expected: включает "gpt2" как уже скачанный

# 8. SentencePiece с HF моделью
lg render ctx:all --lib sentencepiece --encoder google/gemma-2-2b --ctx-limit 1000000

# 9. Проверка кеша
ls -la lg-cfg/tokenizer-models/tokenizers/
ls -la lg-cfg/tokenizer-models/sentencepiece/
```

### 6.2. Проверка ошибок

```bash
# Неизвестная библиотека
lg list encoders --lib unknown
# Expected: ValueError с сообщением

# Отсутствует --lib для encoders
lg list encoders
# Expected: Error message

# Неизвестный энкодер tiktoken
lg render ctx:all --lib tiktoken --encoder unknown --ctx-limit 128000
# Expected: ValueError со списком доступных

# Несуществующая HF модель
lg render ctx:all --lib tokenizers --encoder fake/model --ctx-limit 128000
# Expected: RuntimeError с подсказкой
```

---

## 7. Документация

### 7.1. Обновить README.md

**Добавить раздел "Токенизация и статистика"**:

````markdown
## Токенизация и статистика

LG поддерживает несколько библиотек токенизации для расчета статистики по токенам:

- **tiktoken** (OpenAI) - для GPT-моделей
- **tokenizers** (HuggingFace) - универсальная библиотека с множеством алгоритмов
- **sentencepiece** (Google) - для Gemini и открытых моделей

### Использование

При вызове `render` или `report` укажите три обязательных параметра:

```bash
lg report ctx:all \
  --lib tiktoken \
  --encoder cl100k_base \
  --ctx-limit 128000
```

### Список доступных библиотек

```bash
lg list tokenizer-libs
```

### Список энкодеров для библиотеки

```bash
lg list encoders --lib tiktoken
lg list encoders --lib tokenizers
lg list encoders --lib sentencepiece
```

При первом использовании модели из HuggingFace будут автоматически скачаны и закешированы в `lg-cfg/tokenizer-models/`.

### Рекомендации по выбору

| Если используете... | Рекомендация |
|---------------------|--------------|
| GPT-4, GPT-3.5 | `--lib tiktoken --encoder cl100k_base` |
| GPT-4o, o1, o3 | `--lib tiktoken --encoder o200k_base` |
| Claude 3.5 | `--lib sentencepiece --encoder google/gemma-2-2b` (приближение) |
| Gemini 2.5 | `--lib sentencepiece --encoder google/gemma-2-2b` |
| Grok | `--lib tokenizers --encoder gpt2` (приближение) |
| Llama 3 | `--lib sentencepiece --encoder meta-llama/Llama-2-7b-hf` |
````

---

## 8. Чеклист реализации

### Этап 1: Удаление старого кода

- [ ] Удалить `lg/stats/load.py`
- [ ] Удалить `lg/stats/model.py`
- [ ] Удалить из `lg/stats/__init__.py` экспорты: `load_models`, `list_models`, `get_model_info`, `ModelInfo`, `ModelsConfig`, `PlanInfo`, `ResolvedModel`
- [ ] Удалить аргумент `--model` из CLI (`lg/cli.py`)
- [ ] Удалить подкоманду `lg list models` из CLI
- [ ] Удалить поле `model` из `RunOptions` в `lg/types.py`

### Этап 2: Создание новой инфраструктуры токенизации

- [ ] Создать `lg/stats/tokenizers/__init__.py`
- [ ] Создать `lg/stats/tokenizers/base.py` (BaseTokenizer)
- [ ] Создать `lg/stats/tokenizers/model_cache.py` (ModelCache)
- [ ] Создать `lg/stats/tokenizers/tiktoken_adapter.py` (TiktokenAdapter)
- [ ] Создать `lg/stats/tokenizers/hf_adapter.py` (HFAdapter)
- [ ] Создать `lg/stats/tokenizers/sp_adapter.py` (SPAdapter)
- [ ] Обновить `lg/stats/tokenizers/__init__.py` (фабрика и экспорты)

### Этап 3: Интеграция с существующим кодом

- [ ] Переписать `lg/stats/tokenizer.py` (TokenService как обёртка)
- [ ] Обновить `lg/stats/__init__.py` (новые экспорты)
- [ ] Обновить `lg/stats/report_schema.py` (protocol 5, новые поля)
- [ ] Обновить `lg/stats/report_builder.py` (убрать логику планов)
- [ ] Обновить `lg/stats/collector.py` (заменить model_info на прямой доступ)
- [ ] Обновить `lg/protocol.py` (PROTOCOL_VERSION = 5)
- [ ] Обновить `lg/types.py` (RunOptions: добавить tokenizer_lib/encoder/ctx_limit)
- [ ] Обновить `lg/run_context.py` (создание TokenService с новыми параметрами)

### Этап 4: CLI

- [ ] Добавить `--lib`, `--encoder`, `--ctx-limit` в команды `render`/`report`
- [ ] Обновить `_opts()` для создания RunOptions с новыми параметрами
- [ ] Добавить `tokenizer-libs` в choices для `lg list`
- [ ] Добавить `encoders` в choices для `lg list` с опцией `--lib`
- [ ] Реализовать обработку `lg list tokenizer-libs`
- [ ] Реализовать обработку `lg list encoders --lib <lib>`

### Этап 5: Зависимости

- [ ] Добавить в `pyproject.toml`: `tokenizers>=0.15`
- [ ] Добавить в `pyproject.toml`: `sentencepiece>=0.2`
- [ ] Добавить в `pyproject.toml`: `huggingface-hub>=0.20`

### Этап 6: Миграция

- [ ] Создать `lg/migrate/migrations/m006_remove_models_yaml.py`
- [ ] Зарегистрировать M006 в `lg/migrate/registry.py`

### Этап 7: Тестирование

- [ ] Ручное тестирование всех новых команд
- [ ] Проверка автозагрузки моделей
- [ ] Проверка кеширования
- [ ] Проверка JSON схемы (protocol 5)
- [ ] Проверка обработки ошибок

### Этап 8: Документация

- [ ] Обновить README.md (раздел о токенизации)
- [ ] Добавить примеры использования
- [ ] Добавить таблицу рекомендаций

---

## 9. Возможные проблемы и решения

### Проблема 1: Медленная первая загрузка модели

**Симптом**: При первом использовании `--lib tokenizers --encoder bert-base-uncased` долго висит без вывода.

**Решение**: Добавить логирование прогресса загрузки в адаптеры.

```python
# В hf_adapter.py и sp_adapter.py
logger.info(f"Downloading model '{model_name}' from HuggingFace Hub...")
# После загрузки:
logger.info(f"Model '{model_name}' downloaded and cached successfully")
```

### Проблема 2: Конфликт с существующим кешем HuggingFace

**Симптом**: Модели скачиваются в `~/.cache/huggingface/` вместо `lg-cfg/tokenizer-models/`.

**Решение**: Убедиться что в `hf_hub_download` передаются параметры:
```python
local_dir=str(cache_dir),
local_dir_use_symlinks=False,
```

### Проблема 3: SentencePiece модель не найдена в HF репозитории

**Симптом**: Ошибка при попытке загрузить модель: "Could not find SentencePiece model file".

**Решение**: Проверить наличие файла в репозитории. Некоторые модели хранят токенизатор под разными именами. Расширить список проверяемых имен в `sp_adapter.py`:

```python
for filename in ["tokenizer.model", "spiece.model", "sentencepiece.model", "sp.model"]:
    # ...
```

### Проблема 4: Несовместимость версий библиотек

**Симптом**: Import errors или runtime errors при использовании токенизаторов.

**Решение**: Зафиксировать минимальные версии в `pyproject.toml` и протестировать на чистом окружении.

---

## 10. Итоговая архитектура (диаграмма)

```
CLI (lg/cli.py)
  └─> parse args: --lib, --encoder, --ctx-limit
       └─> RunOptions
            └─> RunContext
                 └─> TokenService
                      └─> create_tokenizer(lib, encoder, ctx_limit, root)
                           ├─> TiktokenAdapter (встроенные encodings)
                           ├─> HFAdapter (HF Hub + ModelCache)
                           └─> SPAdapter (HF Hub + ModelCache + локальные файлы)

ModelCache (lg/stats/tokenizers/model_cache.py)
  └─> lg-cfg/tokenizer-models/
       ├─> tokenizers/
       │    ├─> gpt2/
       │    ├─> bert-base-uncased/
       │    └─> google--gemma-tokenizer/
       └─> sentencepiece/
            ├─> google--gemma-2-2b/
            └─> meta-llama--Llama-2-7b-hf/

StatsCollector
  └─> count_text_cached(text)
       └─> TokenService.count_text_cached()
            └─> BaseTokenizer.count_tokens()

RunResult (protocol 5)
  ├─ tokenizerLib: "tiktoken" | "tokenizers" | "sentencepiece"
  ├─ encoder: "cl100k_base" | "gpt2" | "google/gemma-2-2b"
  └─ ctxLimit: 128000
```
