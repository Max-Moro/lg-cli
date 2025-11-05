# Рекомендации в рамках технологического стека

Данный проект является CLI инструментом и разрабатывается на Python.

## Пути файлов

**КРИТИЧЕСКИ ВАЖНО**: Данный проект работает на Windows. При использовании инструментов Read/Edit/Write всегда используй **обратные слеши** (`\`) в путях файлов.

**Правильно**:
```
Edit(file_path="F:\workspace\lg\cli\lg\template\common.py", ...)
Read(file_path="F:\workspace\lg\cli\tests\template\test_context.py")
```

**Неправильно (вызовет ошибку)**:
```
Edit(file_path="F:/workspace/lg/cli/lg/template/common.py", ...)  # ❌ Прямые слеши
```

**Диагностика проблемы**:
- Если получаешь ошибку "File has been unexpectedly modified. Read it again before attempting to write it"
- И git status показывает чистое дерево
- **Проверь слеши в пути файла** — скорее всего используешь `/` вместо `\`

**Получение правильного пути**:
- Read tool возвращает пути с правильными слешами в начале вывода
- Копируй путь из вывода Read tool для последующих Edit/Write операций
