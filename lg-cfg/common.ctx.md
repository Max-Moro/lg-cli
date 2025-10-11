${docs/intro}

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
{% endif %} {% if task AND scope:local %}
---

# Описание текущей задачи

${task}{% endif %}