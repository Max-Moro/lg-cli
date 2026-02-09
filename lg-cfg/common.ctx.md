---
include: ["ai-interaction", "dev-stage", "common"]
---
{% if scope:local AND tag:agent %}
${tpl:agent/index}

---
{% endif %}
${docs/intro}
{% if tag:src-cli %}
---
{% if tag:review %}
# Changed source code in current branch

${review}

{% else %}
# Source code

${src}

{% endif %}{% if tag:tests AND NOT tag:review %}
## Test code

${tests}
{% endif %}{% endif %}{% if tag:docs %}
---

# Extended documentation

${md:docs/en/*}
{% endif %}{% if task AND scope:local %}
---

# Current task description

${task}{% endif %}
{% if scope:local AND tag:agent %}
${tpl:agent/footer}
{% endif %}