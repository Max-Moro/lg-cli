${md:README}

---
{% if tag:review %}
# Changed source code in current branch
{% else %}
# Source code
{% endif %}
{% if tag:tests %}## Main code{% endif %}

${src}
{% if tag:tests %}
## Test code

${tests}
{% endif %} {% if task AND scope:local %}
---

# Current task description

${task}{% endif %}