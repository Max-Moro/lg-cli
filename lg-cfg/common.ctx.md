${docs/intro}
{% if scope:local OR tag:src-cli %}
---
{% if tag:review %}
# Измененный исходный код в текущей ветке
{% else %}
# Исходный код
{% endif %}
{% if tag:tests %}## Основной код{% endif %}

${src}
{% if tag:tests %}
## Unit-тесты

${tests}
{% endif %}{% endif %}{% if tag:docs %}
---

# Расширенная документация

${md:docs/*}
{% endif %}{% if task AND scope:local %}
---

# Описание текущей задачи

${task}{% endif %}