"""
Тесты для поддержки локальных файлов токенизаторов HuggingFace.
"""

import json

import pytest

from lg.stats.tokenizers import HFAdapter


@pytest.fixture
def simple_tokenizer_json():
    """Создает простой валидный tokenizer.json для тестов."""
    # Минимальный валидный токенизатор (BPE)
    tokenizer_config = {
        "version": "1.0",
        "truncation": None,
        "padding": None,
        "added_tokens": [],
        "normalizer": None,
        "pre_tokenizer": {
            "type": "ByteLevel",
            "add_prefix_space": False,
            "trim_offsets": True,
            "use_regex": True
        },
        "post_processor": None,
        "decoder": {
            "type": "ByteLevel",
            "add_prefix_space": True,
            "trim_offsets": True,
            "use_regex": True
        },
        "model": {
            "type": "BPE",
            "dropout": None,
            "unk_token": None,
            "continuing_subword_prefix": None,
            "end_of_word_suffix": None,
            "fuse_unk": False,
            "byte_fallback": False,
            "vocab": {
                "a": 0,
                "b": 1,
                "c": 2,
                "ab": 3,
                "bc": 4
            },
            "merges": [
                "a b",
                "b c"
            ]
        }
    }
    return tokenizer_config


def test_load_from_local_file(simple_tokenizer_json, tmp_path):
    """Тест загрузки токенизатора из локального файла."""
    # Создаем временный файл tokenizer.json
    tokenizer_file = tmp_path / "tokenizer.json"
    with open(tokenizer_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)
    
    # Загружаем токенизатор из файла
    adapter = HFAdapter(str(tokenizer_file), tmp_path)
    
    # Проверяем, что токенизатор работает
    text = "abc"
    token_count = adapter.count_tokens(text)
    assert token_count > 0
    
    # Проверяем encode/decode
    tokens = adapter.encode(text)
    assert isinstance(tokens, list)
    assert len(tokens) > 0
    
    decoded = adapter.decode(tokens)
    assert isinstance(decoded, str)
    
    # Проверяем, что модель появилась в списке доступных
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "tokenizer" in available  # имя файла без расширения


def test_load_from_local_directory(simple_tokenizer_json, tmp_path):
    """Тест загрузки токенизатора из директории."""
    # Создаем директорию с tokenizer.json
    model_dir = tmp_path / "my_model"
    model_dir.mkdir()
    
    tokenizer_file = model_dir / "tokenizer.json"
    with open(tokenizer_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)
    
    # Загружаем токенизатор из директории
    adapter = HFAdapter(str(model_dir), tmp_path)
    
    # Проверяем, что токенизатор работает
    text = "abc"
    token_count = adapter.count_tokens(text)
    assert token_count > 0
    
    # Проверяем, что модель появилась в списке доступных
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "my_model" in available  # имя директории


def test_local_file_not_found(tmp_path):
    """Тест ошибки при отсутствии локального файла."""
    nonexistent = tmp_path / "nonexistent.json"
    
    # Должна быть попытка скачать с HF Hub и ошибка
    with pytest.raises(RuntimeError, match="Failed to load tokenizer"):
        HFAdapter(str(nonexistent), tmp_path)


def test_local_directory_without_tokenizer_json(tmp_path):
    """Тест ошибки при отсутствии tokenizer.json в директории."""
    empty_dir = tmp_path / "empty_model"
    empty_dir.mkdir()
    
    with pytest.raises(FileNotFoundError, match="does not contain tokenizer.json"):
        HFAdapter(str(empty_dir), tmp_path)


def test_list_encoders_includes_hint(tmp_path):
    """Тест, что список энкодеров содержит подсказку про локальные файлы."""
    encoders = HFAdapter.list_available_encoders(tmp_path)
    
    # Проверяем наличие подсказки
    hints = [e for e in encoders if "local file" in e.lower()]
    assert len(hints) > 0
    assert any("tokenizer.json" in hint for hint in hints)


def test_local_model_persists_in_cache(simple_tokenizer_json, tmp_path):
    """Тест, что локальная модель сохраняется в кэше после первой загрузки."""
    # Создаем временный файл tokenizer.json вне кэша
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    tokenizer_file = external_dir / "custom_tokenizer.json"
    with open(tokenizer_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)
    
    # Первая загрузка - импортирует в кэш
    adapter1 = HFAdapter(str(tokenizer_file), tmp_path)
    text = "test"
    tokens1 = adapter1.count_tokens(text)
    
    # Проверяем, что модель есть в кэше
    cache_dir = tmp_path / ".lg-cache" / "tokenizer-models" / "tokenizers" / "custom_tokenizer"
    assert cache_dir.exists()
    assert (cache_dir / "tokenizer.json").exists()
    
    # Удаляем оригинальный файл
    tokenizer_file.unlink()
    
    # Вторая загрузка - должна работать из кэша по короткому имени
    adapter2 = HFAdapter("custom_tokenizer", tmp_path)
    tokens2 = adapter2.count_tokens(text)
    
    # Результаты должны совпадать
    assert tokens1 == tokens2
    
    # Модель должна быть в списке доступных
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "custom_tokenizer" in available


def test_reusing_imported_model_by_name(simple_tokenizer_json, tmp_path):
    """Тест переиспользования импортированной модели по короткому имени."""
    # Импортируем модель из локального файла
    external_file = tmp_path / "external" / "my_special_tokenizer.json"
    external_file.parent.mkdir()
    with open(external_file, "w", encoding="utf-8") as f:
        json.dump(simple_tokenizer_json, f)
    
    # Первая загрузка с полным путем - импортирует в кэш
    adapter1 = HFAdapter(str(external_file), tmp_path)
    
    # Проверяем, что модель доступна в списке
    available = HFAdapter.list_available_encoders(tmp_path)
    assert "my_special_tokenizer" in available
    
    # Вторая загрузка по короткому имени - должна работать
    adapter2 = HFAdapter("my_special_tokenizer", tmp_path)
    
    # Обе должны работать одинаково
    text = "Hello world"
    assert adapter1.count_tokens(text) == adapter2.count_tokens(text)
