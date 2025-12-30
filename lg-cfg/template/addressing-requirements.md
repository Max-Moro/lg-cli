# Система адресации в шаблонах LG — Требования (ТЗ)

> Этот документ описывает целевую систему адресации путей внутри плейсхолдеров шаблонизатора Listing Generator.

---

## 1. Общая концепция

Система адресации в плейсхолдерах шаблонов LG должна поддерживать **три уровня спецификации пути**:

```
<скоуп> + <путь_внутри_lg-cfg> + <ресурс>
```

### 1.1. Скоуп (Scope)

**Скоуп** — это путь к модулю в репозитории, содержащему свою директорию `lg-cfg/`.

- **Неявный скоуп**: определяется контекстом текущего обрабатываемого шаблона
- **Явный скоуп `@self`**: текущий скоуп (эквивалентен неявному)
- **Явный скоуп `@<path>`**: путь к другому модулю относительно текущего скоупа

Примеры:
```markdown
${tpl:intro}              # неявный скоуп (текущий)
${tpl@self:intro}         # явный текущий скоуп
${tpl@apps/web:guide}     # скоуп apps/web (относительно текущего)
${tpl@[libs/core:v2]:api} # скоуп с двоеточием в пути (bracket-синтаксис)
${tpl@/:common}           # корневой скоуп (абсолютный)
```

### 1.2. Путь внутри lg-cfg

Определяет директорию внутри `lg-cfg/`, где ищется ресурс.

- **Относительный путь**: не начинается с `/`, разрешается относительно **текущей директории активного шаблона**
- **Абсолютный путь**: начинается с `/`, разрешается относительно корня `lg-cfg/`
- **Подъём по директориям**: поддерживается нотация `../` для перехода на уровень выше

Примеры:
```markdown
# Из lg-cfg/adapters/_.ctx.md

${tpl:intro}              # ищем lg-cfg/adapters/intro.tpl.md
${tpl:/common/intro}      # ищем lg-cfg/common/intro.tpl.md (абсолютный)
${tpl:../common/intro}    # ищем lg-cfg/common/intro.tpl.md (относительный с подъёмом)
${tpl:../../outside}      # ОШИБКА: попытка выйти за пределы lg-cfg/
```

**Нормализация путей**:
- Путь нормализуется после разрешения (убираются `.` и `..`)
- Попытка выйти за пределы `lg-cfg/` через `../` приводит к **ошибке**
- Пример: из `lg-cfg/a/b/c/` путь `../../../x` разрешается в `lg-cfg/x`
- Пример: из `lg-cfg/a/` путь `../../x` — **ОШИБКА** (выход за пределы)

### 1.3. Контекст текущей директории

**Текущая директория** — это директория, где находится **активный обрабатываемый файл** шаблона. При вложенных включениях контекст меняется динамически.

Пример:
```
lg-cfg/
├─ main.ctx.md           # содержит ${tpl:adapters/intro}
└─ adapters/
   ├─ intro.tpl.md       # содержит ${md@self:budget}
   └─ budget.md
```

При обработке `main.ctx.md`:
1. Текущая директория = `lg-cfg/`
2. `${tpl:adapters/intro}` → загружается `lg-cfg/adapters/intro.tpl.md`
3. Текущая директория меняется на `lg-cfg/adapters/`
4. `${md@self:budget}` → ищем `lg-cfg/adapters/budget.md` ✓

---

## 2. Типы плейсхолдеров и их особенности

### 2.1. Секционные плейсхолдеры `${section}`

Вставка секций, определённых в `sections.yaml` или `*.sec.yaml`.

**Канонические ID секций** формируются при загрузке конфига:
- `sections.yaml#docs` → ID = `docs`
- `adapters/_.sec.yaml#src` → ID = `adapters/_/src`

**Относительность для секций**:
- Относительный путь разрешается как `<текущая_директория>/<имя_секции>`
- Fallback на корневые секции **НЕ** применяется
- Абсолютный путь (с `/`) разрешается от корня `lg-cfg/`

Примеры:
```markdown
# Из lg-cfg/adapters/_.ctx.md

${src}                    # ищем секцию с ID "adapters/src" — НЕ найдена, ОШИБКА
${_/src}                  # ищем секцию с ID "adapters/_/src" ✓
${/docs}                  # ищем секцию с ID "docs" (корневая) ✓
${@apps/web:web-src}      # ищем секцию "web-src" в скоупе apps/web
```

**Особенность `sections.yaml`**: Секции из файла `sections.yaml` (в отличие от `*.sec.yaml`) регистрируются без префикса пути. Это единственное исключение в системе именования.

### 2.2. Шаблонные плейсхолдеры `${tpl:...}`

Вставка шаблонов из `*.tpl.md` файлов.

**Синтаксис**:
```markdown
${tpl:name}               # относительный путь
${tpl:/path/name}         # абсолютный путь внутри lg-cfg/
${tpl@origin:name}        # с указанием скоупа
${tpl@[origin]:name}      # bracket-синтаксис для origin с ":"
```

**Расширение файла**:
- `.tpl.md` добавляется автоматически, если не указано
- Можно указать явно: `${tpl:intro.tpl.md}`

Примеры:
```markdown
# Из lg-cfg/docs/_.ctx.md

${tpl:header}             # lg-cfg/docs/header.tpl.md
${tpl:/common/header}     # lg-cfg/common/header.tpl.md
${tpl@libs/core:api}      # libs/core/lg-cfg/api.tpl.md
```

### 2.3. Контекстные плейсхолдеры `${ctx:...}`

Вставка контекстов из `*.ctx.md` файлов. Правила идентичны `${tpl:...}`.

**Синтаксис**:
```markdown
${ctx:name}               # относительный путь
${ctx:/path/name}         # абсолютный путь внутри lg-cfg/
${ctx@origin:name}        # с указанием скоупа
```

**Расширение файла**:
- `.ctx.md` добавляется автоматически, если не указано

### 2.4. Markdown плейсхолдеры `${md:...}`

Вставка Markdown-документов. Имеет **два режима работы** в зависимости от наличия `@`.

#### Режим без `@` — файлы вне lg-cfg/

```markdown
${md:path}                # путь относительно текущего скоупа (вне lg-cfg/)
```

Используется для вставки документации из `docs/`, `README.md` и других файлов **за пределами** `lg-cfg/`, но **внутри текущего скоупа**.

Примеры:
```markdown
# Из корневого скоупа:
${md:README}              # <repo>/README.md
${md:docs/api}            # <repo>/docs/api.md

# Из скоупа apps/web:
${md:README}              # <repo>/apps/web/README.md
${md:docs/guide}          # <repo>/apps/web/docs/guide.md
```

**Особенности**:
- Путь относительно текущего скоупа (директории, содержащей lg-cfg/)
- При вложенных включениях меняется вместе со скоупом
- Расширение `.md` добавляется автоматически, если не указано

#### Режим с `@` — файлы внутри lg-cfg/

```markdown
${md@self:path}           # файл внутри текущего lg-cfg/
${md@origin:path}         # файл внутри lg-cfg/ другого скоупа
```

**Относительность работает** как для других плейсхолдеров:
```markdown
# Из lg-cfg/adapters/_.ctx.md

${md@self:budget}         # lg-cfg/adapters/budget.md
${md@self:/design}        # lg-cfg/design.md
${md@libs/core:api}       # libs/core/lg-cfg/api.md
```

#### Дополнительные параметры md-плейсхолдеров

```markdown
${md:docs/api#Authentication}           # частичное включение по якорю
${md:docs/api, level:3, strip_h1:true}  # явные параметры
${md:docs/guides/*}                     # glob-паттерн
${md:docs/deploy, if:tag:cloud}         # условное включение
```

---

## 3. Правила разрешения путей

### 3.1. Алгоритм разрешения

1. **Определить скоуп**:
   - Если указан `@origin` → использовать указанный скоуп
   - Если указан `@self` → использовать текущий скоуп
   - Если `@` не указан → использовать текущий скоуп (для md без @ — см. п. 2.4)

2. **Определить базовую директорию внутри lg-cfg/**:
   - Если путь начинается с `/` → базовая директория = корень `lg-cfg/`
   - Иначе → базовая директория = текущая директория активного шаблона

3. **Разрешить полный путь**:
   - Объединить базовую директорию и указанный путь
   - Добавить расширение файла, если не указано

4. **Проверить существование**:
   - Если ресурс не найден → **ОШИБКА** (без fallback)

### 3.2. Без Fallback-логики

Система **НЕ** использует fallback при разрешении путей. Если ресурс не найден по указанному пути — это ошибка.

```markdown
# Из lg-cfg/adapters/_.ctx.md

${tpl:common}             # ОШИБКА: lg-cfg/adapters/common.tpl.md не существует
${tpl:/common}            # OK: lg-cfg/common.tpl.md
```

Обоснование: fallback создаёт неявное поведение и маскирует ошибки в путях.

### 3.3. Обработка расширений файлов

| Плейсхолдер | Авто-расширение | Пример |
|-------------|-----------------|--------|
| `${tpl:...}` | `.tpl.md` | `intro` → `intro.tpl.md` |
| `${ctx:...}` | `.ctx.md` | `main` → `main.ctx.md` |
| `${md:...}` | `.md` | `guide` → `guide.md` |

**Нестандартные расширения** (например, `.mdc` для Cursor) должны указываться явно:
```markdown
${md@self:rules.mdc}      # явное указание нестандартного расширения
```

---

## 4. Стек контекста директорий

При обработке вложенных включений поддерживается **стек контекста**.

### 4.1. Структура стека

Каждый элемент стека содержит:
- `origin` — текущий скоуп (путь к модулю)
- `current_dir` — текущая директория внутри lg-cfg/ этого скоупа

### 4.2. Операции со стеком

**Push** — при входе в `${tpl:...}` или `${ctx:...}`:
- Если origin изменился (указан `@origin`) → push нового origin
- Обновить current_dir на директорию загружаемого файла

**Pop** — при выходе из обработанного включения:
- Восстановить предыдущий контекст

### 4.3. Пример работы стека

```
lg-cfg/
├─ main.ctx.md                    # ${tpl:docs/intro}
├─ common/
│  └─ header.tpl.md
└─ docs/
   ├─ intro.tpl.md                # ${tpl:../common/header} — OK (подъём на уровень выше)
   │                              # ${tpl:/common/header} — OK (абсолютный путь)
   └─ api.tpl.md
```

```
apps/web/lg-cfg/
├─ web.ctx.md                     # ${ctx@/:main}
└─ components/
   └─ button.tpl.md
```

Трассировка для `apps/web/lg-cfg/web.ctx.md`:
1. Стек: `[{origin: "apps/web", current_dir: ""}]`
2. `${ctx@/:main}` → push `{origin: "", current_dir: ""}]` (корневой скоуп через /)
3. Стек: `[{origin: "apps/web", current_dir: ""}, {origin: "", current_dir: ""}]`
4. Внутри main.ctx.md: `${tpl:docs/intro}` → current_dir = "docs"
5. Стек: `[..., {origin: "", current_dir: "docs"}]`
6. После обработки intro.tpl.md → pop
7. И т.д.

**Примечание**: `@/` означает корневой скоуп. Без `/`, скоуп `@path` разрешается относительно текущего.

---

## 5. Специальные случаи

### 5.1. Корневой скоуп

Для обращения к корневому скоупу из дочернего модуля:
```markdown
${tpl@/:common}           # корневой lg-cfg/common.tpl.md
${@/:root-section}        # корневая секция
```

Пустой путь после `@` означает корень репозитория.

### 5.2. Bracket-синтаксис для сложных origin

Если origin содержит двоеточие:
```markdown
${tpl@[libs/core:v2]:api}
${@[apps/web:legacy]:web-src}
```

### 5.3. Секции из sections.yaml vs *.sec.yaml

| Источник | Файл | Секция | Канонический ID |
|----------|------|--------|-----------------|
| Корневой | `sections.yaml` | `docs` | `docs` |
| Фрагмент (1 секция) | `adapters.sec.yaml` | `core` | `core` |
| Фрагмент (N секций) | `adapters.sec.yaml` | `core` | `adapters/core` |
| Вложенный фрагмент | `api/v1.sec.yaml` | `handlers` | `api/handlers` или `api/v1/handlers` |

**Правило для фрагментов с одной секцией**: если `*.sec.yaml` содержит ровно одну секцию, её канонический ID = имя секции (без префикса пути файла).

---

## 6. Сообщения об ошибках

Система должна предоставлять информативные сообщения об ошибках:

### 6.1. Ресурс не найден

```
TemplateProcessingError: Template 'intro' not found
  Location: lg-cfg/adapters/_.ctx.md:15
  Searched: lg-cfg/adapters/intro.tpl.md
  Hint: Use absolute path '/intro' to search from lg-cfg/ root
```

### 6.2. Секция не найдена

```
TemplateProcessingError: Section 'src' not found
  Location: lg-cfg/adapters/_.ctx.md:20
  Searched: Section with ID 'adapters/src'
  Available sections in current scope:
    - adapters/_/src
    - adapters/_/tests
  Hint: Did you mean '${_/src}'?
```

### 6.3. Скоуп не найден

```
TemplateProcessingError: Scope 'apps/mobile' not found
  Location: lg-cfg/main.ctx.md:10
  Searched: apps/mobile/lg-cfg/
  Hint: Ensure the module has lg-cfg/ directory
```

---

## 7. Примеры использования

### 7.1. Типичная структура проекта

```
project/
├─ README.md
├─ docs/
│  ├─ api.md
│  └─ guide.md
│
├─ lg-cfg/
│  ├─ sections.yaml              # docs, src, tests
│  ├─ common.ctx.md
│  ├─ common/
│  │  ├─ header.tpl.md
│  │  └─ footer.tpl.md
│  └─ adapters/
│     ├─ _.sec.yaml              # adapters/_/src, adapters/_/tests
│     ├─ _.ctx.md
│     ├─ budget.md
│     └─ design.md
│
└─ apps/web/
   ├─ src/
   └─ lg-cfg/
      ├─ sections.yaml           # web-src, web-docs
      └─ web.ctx.md
```

### 7.2. Примеры плейсхолдеров из разных контекстов

**Из `lg-cfg/common.ctx.md`**:
```markdown
${tpl:common/header}              # lg-cfg/common/header.tpl.md
${docs}                           # секция "docs" из sections.yaml
${md:README}                      # <repo>/README.md
${md:docs/api}                    # <repo>/docs/api.md
```

**Из `lg-cfg/adapters/_.ctx.md`**:
```markdown
${tpl:design-notes}               # lg-cfg/adapters/design-notes.tpl.md — если есть
${tpl:/common/header}             # lg-cfg/common/header.tpl.md
${_/src}                          # секция "adapters/_/src"
${/docs}                          # секция "docs" (корневая)
${md@self:budget}                 # lg-cfg/adapters/budget.md
${md@self:/design}                # lg-cfg/design.md — если есть в корне
${md:docs/api}                    # <repo>/docs/api.md
```

**Из `apps/web/lg-cfg/web.ctx.md`**:
```markdown
${web-src}                        # секция "web-src" из локального sections.yaml
${tpl@/:common/header}            # <repo>/lg-cfg/common/header.tpl.md (корневой скоуп)
${@/:docs}                        # секция "docs" из корневого скоупа
${md:README}                      # apps/web/README.md (текущий скоуп!)
${md@self:deployment}             # apps/web/lg-cfg/deployment.md
```

---

## 8. Не поддерживаемые возможности

Следующие возможности явно **НЕ поддерживаются**:

1. **Fallback на корень**: если `${tpl:name}` не найден в текущей директории, поиск в корне НЕ производится
2. **Glob-паттерны для tpl/ctx**: `${tpl:common/*}` — НЕ поддерживается (только для md)
3. **Динамические пути**: `${tpl:${var}}` — НЕ поддерживается

---

## 9. Обратная совместимость

**Обратная совместимость НЕ обеспечивается**. Это breaking change.

Все существующие шаблоны и тесты должны быть обновлены для соответствия новой системе адресации. Миграция существующих конфигураций будет выполнена отдельно перед релизом.