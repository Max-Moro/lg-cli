#!/usr/bin/env bash
set -euo pipefail

# Переходим в корень проекта (скрипт лежит в scripts/)
cd "$(dirname "$0")/.."

# Находим виртуальное окружение
if [[ -d ".venv" ]]; then
    VENV_PY="./.venv/Scripts/python"
elif [[ -n "${VIRTUAL_ENV:-}" ]]; then
    VENV_PY="$VIRTUAL_ENV/Scripts/python"
else
    echo "❌ Не найдено виртуальное окружение (.venv или активированное)"
    exit 1
fi

# Генерация моделей из схемы
"$VENV_PY" -m datamodel_code_generator \
  --input lg/run_result.schema.json \
  --input-file-type jsonschema \
  --output lg/api_schema.py \
  --target-python-version 3.11 \
  --use-standard-collections \
  --use-schema-description \
  --enum-field-as-literal one \
  --disable-timestamp \
  --output-model-type pydantic_v2.BaseModel \
  --base-class pydantic.BaseModel \
  --use-field-description \
  --strict-nullable

echo "✅ Модели сгенерированы в lg/api_schema.py"
