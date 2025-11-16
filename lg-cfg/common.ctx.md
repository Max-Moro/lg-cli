{% if scope:local AND tag:agent %}
${tpl:agent/index}

---
{% endif %}
${docs/intro}
{% if scope:local OR tag:src-cli %}
---
{% if tag:review %}
# Changed source code in current branch
{% else %}
# Source code
{% endif %}
{% if tag:tests %}## Main code{% endif %}

${src}
{% if tag:tests %}
## Unit tests

${tests}
{% endif %}{% endif %}{% if tag:docs %}
---

# Расширенная документация

${md:docs/*}
{% endif %}{% if task AND scope:local %}
---

# Current task description

${task}{% endif %}
{% if scope:local AND tag:agent %}
${tpl:agent/footer}
{% endif %}