## Что мы имеем сейчас

У нас сейчас в LG используется 2 способа работы с Markdown-документацией.

### Способ 1

Подразумевает создание родного для LG специально формата Markdown, который описывает контексты и шаблоны. Данные документы вставляются через плейсхолдеры `${tpl:…}` и `${ctx:…}`. Внутри себя они поддерживают все возможности шаблонизатора LG.

Эти "родные" для LG документы расположены внутри `lg-cfg/`
- `lg-cfg/**/*.tpl.md`
- `lg-cfg/**/*.ctx.md`

### Способ 2

Подразумевает вставку уже ранее существующих в кодовой базе Markdown-документов или же новых документов, сгенерированных AI-ассистентами, которые не знают о специфике LG-инсрумента.

Такие документы вставляют через секции. Например, так:
```yaml
markdown:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/markdown.md"
  markdown:
    max_heading_level: 3
```

Эти "не родные" для LG документы сам инструмент может оптимизировать, но через подсистему языковых адаптеров. Текущие варианты оптимизации:
- Удаление разделов по заголовкам (`drop.sections`)
- Удаление YAML front matter (`drop.frontmatter`) 
- Нормализацию заголовков (`max_heading_level`, `strip_single_h1`)
- Плейсхолдеры для удалённого контента (`placeholder`)

## Расширение системы плейсхолдеров

На практике на самом деле мы чаще вставляем в шаблоны именно стороннюю документацию. Поэтому нам сейчас необходимо расширить систему плейсхолдеров, добавив специальный синтаксический сахар для данных случаев. Он позволит производить прямые включения файлов Markdown из шаблонов без необходимости вручную определять секции, с интеллектуальным контекстуальным поведением для уровней заголовков.

Для этих целей мы будем использовать новый префикс `${md:…}`.

### Вставка обычного документа

```markdown
${md:README} <!-- Автоматическое добавление `.md` если расширение не указано -->
```

Это эквивалентно созданию в IR-модели пайплайна временной виртуальной секции:
```yaml
_virtual:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/README.md"
```
и ее вставка в данное место через ${_virtual}.

### Вставка документа из поддиректории

```markdown
${md:docs/markdown}
```

Это эквивалентно вставке секции:
```yaml
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/markdown.md"
```

### Вставка документа, помещенного в `lg-cfg/`

```markdown
${md@self:adapters/gen/TREE_SITTER_README}
```

Это эквивалентно вставке секции:
```yaml
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/lg-cfg/adapters/gen/TREE_SITTER_README.md"
```

Для данной секции фильтр файловой системы по `lg-cfg/` в раннем прунере отключается.

### Вставка документа из другого федеративного скоупа

```markdown
${md@apps/web:web-intro}
```

Это эквивалентно вставке секции:
```yaml
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/apps/web/lg-cfg/web-intro.md"
```

### Удобный синтаксический сахар для управления заголовками

~~~markdown
# Listing Generator 

## Расширенная документация

### ${md:docs/templates}

### ${md:docs/markdown}

### ${md:docs/adapters}
~~~

На самом деле приведет к созданию и применению виртуальных секций:
```yaml
_virtual_000:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/templates.md"
  markdown:
    max_heading_level: 3 # Персер понял, что плейсхолдер вставляется в зоголовок уровня 3 по наличию `###`

_virtual_001:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/markdown.md"
  markdown:
    max_heading_level: 3

_virtual_002:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/adapters.md"
  markdown:
    max_heading_level: 3
```

### Удобный синтаксический сахар для определения ситуации необходимости удаления заголовка 1-го уровня

~~~markdown
# Listing Generator 

## Расширенная документация

### Шаблоны, контексты и каскадные включения

${md:docs/templates}

### Руководство по работе с Markdown

${md:docs/markdown}

### Языковые адаптеры

${md:docs/markdown}
~~~

На самом деле приведет к созданию и применению виртуальных секций:
```yaml
_virtual_000:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/templates.md"
  markdown:
    max_heading_level: 4 # Весь этот раздел внутри 3-го уровня
    strip_single_h1: true # Персер понял, что общий заголовок 3-го уровня параграфа есть уже в родительском шаблоне

_virtual_001:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/markdown.md"
  markdown:
    max_heading_level: 4
    strip_single_h1: true

_virtual_002:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/adapters.md"
  markdown:
    max_heading_level: 4
    strip_single_h1: true
```

### Еще один вариант синтаксического сахара

~~~markdown
# Listing Generator 

## Расширенная документация

${md:docs/templates}

${md:docs/markdown}

${md:docs/markdown}

## Лицензия
~~~

На самом деле приведет к созданию и применению виртуальных секций:
```yaml
_virtual_000:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/templates.md"
  markdown:
    max_heading_level: 3 # Весь этот раздел внутри 2-го уровня
    strip_single_h1: false # Заголовки 1-го уровня нужны и они опускаются до 3-го уровня

_virtual_001:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/markdown.md"
  markdown:
    max_heading_level: 3
    strip_single_h1: false

_virtual_002:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/docs/adapters.md"
  markdown:
    max_heading_level: 3
    strip_single_h1: false
```

### Явное переопределение настроек через параметры

```markdown
${md:docs/templates, level:4, strip_h1:false}
```

Это позволит пользователям точно управлять поведением в особых случаях, при этом сохраняя преимущества автоматики.

### Частичное включение документа

```markdown
${md:docs/api#Authentication}
```

```yaml
…
  markdown:
    drop:
      sections:
        - match: { kind: text, pattern: "Authentication" }
…
```

Включение только определённого параграфа документации по заголовку, что полезно для больших документов.

### Массовое добавление документации и поддержка глобов

```markdown
${md:docs/guides/*}  <!-- все руководства -->
```

```yaml
…
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/guides/*"
…
```

### Синтаксический сахар для условного включения

```markdown
${md:docs/deployment, if:tag:cloud}
```

Включение документа на основе активных тегов или тегсетов.
