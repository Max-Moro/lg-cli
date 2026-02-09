---
include: ["ai-interaction", "dev-stage"]
---
{% if scope:local AND tag:agent %}
${tpl:agent/index}

---
{% endif %}
${md:README}

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
{% endif %}{% if tag:docs %}
---

# Extended documentation

${md:docs/*}
{% endif %}{% if task AND scope:local %}
---

# Current task description

${task}{% endif %}
{% if scope:local AND tag:agent %}
${tpl:agent/footer}
{% endif %}