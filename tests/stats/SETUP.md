# Настройка тестового окружения для тестов статистики

Тесты в `tests/stats/` используют предскачанные модели токенизации для избежания скачивания с HuggingFace Hub при каждом запуске.

## Быстрый старт

### Вариант 1: Использование только tiktoken (рекомендуется для CI)

Тесты автоматически используют tiktoken (встроенный в библиотеку) когда модели HF/SP недоступны. Просто запустите:

```bash
pytest tests/stats/
```

### Вариант 2: Полное окружение с HF и SentencePiece моделями

Для запуска всех тестов включая сравнения токенизаторов:

1. **Установите зависимости**:
   ```bash
   pip install tokenizers sentencepiece huggingface-hub
   ```

2. **Скачайте тестовые модели**:
   ```bash
   python tests/stats/download_test_models.py
   ```
   
   Или вручную следуя инструкциям в `tests/stats/resources/README.md`

3. **Запустите тесты**:
   ```bash
   pytest tests/stats/
   ```

## Структура

```
tests/stats/
├── __init__.py                      # Описание пакета
├── conftest.py                      # Фикстуры и mock для HF Hub
├── resources/                       # Предскачанные модели
│   ├── README.md                    # Инструкции по скачиванию
│   ├── models_manifest.json         # Манифест моделей
│   ├── tokenizers/                  # HuggingFace tokenizers
│   │   └── gpt2/
│   │       └── tokenizer.json
│   └── sentencepiece/               # SentencePiece модели
│       └── google--gemma-2-2b/
│           └── tokenizer.model
├── test_model_cache.py              # Тесты кеширования моделей
├── test_tokenizer_comparison.py     # Сравнения токенизаторов
└── test_statistics.py               # Основные тесты статистики
```

## Ключевые фичи

### Mock для HuggingFace Hub

Фикстура `mock_hf_hub` в `conftest.py` подменяет `hf_hub_download` на версию, которая:
- Использует локальные файлы из `resources/`
- Имитирует поведение реального HF Hub
- Отслеживает количество "скачиваний" для тестов кеша

### Фикстуры токенизаторов

- `tiktoken_service` - TokenService с tiktoken (всегда доступен)
- `hf_tokenizer_service` - TokenService с HF tokenizers (требует модели)
- `sp_tokenizer_service` - TokenService с SentencePiece (требует модели)

### Тестовые тексты

Фикстура `sample_texts` предоставляет набор текстов для сравнения:
- `simple` - простой английский текст
- `python_code` - код на Python
- `mixed` - смешанный контент (текст + код + markdown)
- `special_chars` - специальные символы и Unicode
- `long_text` - длинный текст для тестов производительности

## CI/CD

В CI окружении (без HF/SP моделей):
- Тесты автоматически используют tiktoken
- Тесты, требующие HF/SP, пропускаются (skip)
- Базовая функциональность полностью тестируется

Для полного тестирования в CI:
- Скачайте модели один раз
- Закешируйте директорию `tests/stats/resources/`
- Переиспользуйте в последующих запусках

## Добавление новых моделей

1. Обновите `resources/models_manifest.json`
2. Скачайте модель в соответствующую поддиректорию
3. Обновите фикстуры в `conftest.py` при необходимости
4. Добавьте тесты для новой модели

## Troubleshooting

### Ошибка "Model not found in test resources"

Модель не скачана. Решение:
```bash
python tests/stats/download_test_models.py
```

### Тесты HF/SP пропускаются

Нормально для окружений без моделей. Если хотите запустить:
```bash
python tests/stats/download_test_models.py
pytest tests/stats/ -v
```

### Медленные тесты

Проверьте что mock_hf_hub работает:
```bash
pytest tests/stats/test_model_cache.py -v
```

Должны быть сообщения "Loading tokenizer from cache".
