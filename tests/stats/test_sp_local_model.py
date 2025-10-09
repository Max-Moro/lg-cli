"""
Тесты для поддержки локальных файлов SentencePiece моделей.
"""

import pytest
import sentencepiece as spm

from lg.stats.tokenizers import SPAdapter


@pytest.fixture
def simple_sp_model(tmp_path):
    """Создает простую SentencePiece модель для тестов."""
    # Создаем больший корпус для успешного обучения
    text_file = tmp_path / "train.txt"
    # Генерируем разнообразный текст
    corpus = []
    for i in range(1000):
        corpus.append(f"This is sentence number {i} with some words and tokens.")
        corpus.append(f"Python code example: def function_{i}():")
        corpus.append(f"Data {i}: abc xyz {i*2} items")
    text_file.write_text("\n".join(corpus), encoding="utf-8")
    
    # Обучаем модель с меньшим vocab_size
    model_prefix = tmp_path / "test_model"
    spm.SentencePieceTrainer.train(
        input=str(text_file),
        model_prefix=str(model_prefix),
        vocab_size=500,  # Увеличили для успешного обучения
        model_type="unigram",  # unigram работает лучше на малых корпусах
        character_coverage=1.0,
    )
    
    return model_prefix.with_suffix(".model")


def test_load_from_local_file(simple_sp_model, tmp_path):
    """Тест загрузки SentencePiece модели из локального файла."""
    # Загружаем модель из файла
    adapter = SPAdapter(str(simple_sp_model), tmp_path)
    
    # Проверяем, что модель работает
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
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "test_model" in available  # имя файла без расширения


def test_load_from_local_directory(simple_sp_model, tmp_path):
    """Тест загрузки SentencePiece модели из директории."""
    # Создаем директорию и копируем модель
    model_dir = tmp_path / "my_sp_model"
    model_dir.mkdir()
    
    import shutil
    dest_model = model_dir / simple_sp_model.name
    shutil.copy2(simple_sp_model, dest_model)
    
    # Загружаем модель из директории
    adapter = SPAdapter(str(model_dir), tmp_path)
    
    # Проверяем, что модель работает
    text = "abc"
    token_count = adapter.count_tokens(text)
    assert token_count > 0
    
    # Проверяем, что модель появилась в списке доступных
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "my_sp_model" in available  # имя директории


def test_local_model_persists_in_cache(simple_sp_model, tmp_path):
    """Тест, что локальная модель сохраняется в кэше после первой загрузки."""
    # Первая загрузка - импортирует в кэш
    adapter1 = SPAdapter(str(simple_sp_model), tmp_path)
    text = "test"
    tokens1 = adapter1.count_tokens(text)
    
    # Проверяем, что модель есть в кэше
    cache_dir = tmp_path / ".lg-cache" / "tokenizer-models" / "sentencepiece" / "test_model"
    assert cache_dir.exists()
    assert any(cache_dir.glob("*.model"))
    
    # Удаляем оригинальный файл
    simple_sp_model.unlink()
    
    # Вторая загрузка - должна работать из кэша по короткому имени
    adapter2 = SPAdapter("test_model", tmp_path)
    tokens2 = adapter2.count_tokens(text)
    
    # Результаты должны совпадать
    assert tokens1 == tokens2
    
    # Модель должна быть в списке доступных
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "test_model" in available


def test_reusing_imported_model_by_name(simple_sp_model, tmp_path):
    """Тест переиспользования импортированной модели по короткому имени."""
    # Переименовываем модель для теста
    import shutil
    renamed_model = simple_sp_model.parent / "my_custom_model.model"
    shutil.move(str(simple_sp_model), str(renamed_model))
    
    # Первая загрузка с полным путем - импортирует в кэш
    adapter1 = SPAdapter(str(renamed_model), tmp_path)
    
    # Проверяем, что модель доступна в списке
    available = SPAdapter.list_available_encoders(tmp_path)
    assert "my_custom_model" in available
    
    # Вторая загрузка по короткому имени - должна работать
    adapter2 = SPAdapter("my_custom_model", tmp_path)
    
    # Обе должны работать одинаково
    text = "Hello world"
    assert adapter1.count_tokens(text) == adapter2.count_tokens(text)


def test_list_encoders_includes_hint(tmp_path):
    """Тест, что список энкодеров содержит подсказку про локальные файлы."""
    encoders = SPAdapter.list_available_encoders(tmp_path)
    
    # Проверяем наличие подсказки
    hints = [e for e in encoders if "local file" in e.lower()]
    assert len(hints) > 0
    assert any(".spm" in hint for hint in hints)
