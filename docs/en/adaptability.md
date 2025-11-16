# Listing Generator · Adaptive Capabilities

## Functionality Overview

The adaptive capabilities system for Listing Generator allows you to create and use different context slices based on mode sets and tag sets. This system provides flexible configuration of generated contexts without duplicating configuration.

## Key Concepts

### Mode Sets and Modes

**Mode Set** - a group of mutually exclusive options representing a specific aspect of work (for example, "AI Interaction Method", "Development Stage").

**Mode** - a specific option within a mode set that activates certain tags and special settings.

### Tag Sets and Tags

**Tag Set** - a group of related tags representing a specific category (for example, "Programming Languages").

**Tag** - an atomic filtering element that can be activated or deactivated.

## Configuration Structure

### Mode Configuration

```yaml
# lg-cfg/modes.yaml
mode-sets:
  ai-interaction:
    title: "AI Interaction Method"
    modes:
      ask:
        title: "Ask"
        description: "Basic question-answer mode"
        # No special tags or options

      agent:
        title: "Agent Mode"
        description: "Mode with tools"
        tags: [agent, tools]
        # Arbitrary additional options are possible
        allow_tools: true

  dev-stage:
    title: "Feature Development Stage"
    modes:
      planning:
        title: "Planning"
        tags: [architecture, docs]

      development:
        title: "Main Development"

      testing:
        title: "Writing Tests"
        tags: [tests]
        default_task: "Write tests for the current functional module."

      review:
        title: "Code Review"
        tags: [review]
        default_task: "Conduct a code review of the changes and provide improvement recommendations."
        # Arbitrary additional options are possible
        vcs_mode: "branch-changes"

# Including modes from child scopes
include:
  - child1 # Includes child1/lg-cfg/modes.yaml
  - child2 # Includes child2/lg-cfg/modes.yaml
```

## Tag Configuration

```yaml
# lg-cfg/tags.yaml
tag-sets:
  language:
    title: "Programming Languages"
    tags:
      python:
        title: "Python"
      typescript:
        title: "TypeScript"
      javascript:
        title: "JavaScript"

  code-type:
    title: "Code Type"
    tags:
      product:
        title: "Production Code"
      tests:
        title: "Test Code"
      generated:
        title: "Generated Code"

  some-feature-slices:
    title: "Large Functional Module"
    tags:
      subfeature_foo:
        title: "Feature #1"
      subfeature_bar:
        title: "Feature #2"
      subfeature_baz:
        title: "Feature #3"

# Global tags (not part of specific sets and usually toggled through modes)
tags:
  agent:
    title: "Agent Capabilities"
  review:
    title: "Code Review Guidelines"
  # ... other tags

# Including tags from child scopes
include:
  - child1 # Includes child1/lg-cfg/tags.yaml
  - child2 # Includes child2/lg-cfg/tags.yaml
```

If the current repository's starting `lg-cfg` doesn't have its own `modes.yaml` and `tags.yaml` files at all, a reasonable minimal default configuration will be applied.

## CLI

```bash
# List of mode sets with nested modes
# Sufficient data for UI generation (comboboxes)
lg list mode-sets

# List of tag sets with nested tags
# Sufficient data for UI generation (checkbox sets)
lg list tag-sets

# Rendering with specified modes
lg render ctx:my-context --mode ai:agent --mode stage:development

# Rendering with additional tags specified
# In UA, tags are selected through checkbox sets within TAGSET and then form a flat list
lg render ctx:my-context --tags python,minimal

# Combined usage
lg render ctx:my-context --mode ai:agent --mode stage:review --tags python

# Rendering with target branch specified for branch-changes mode
lg render ctx:my-context --mode stage:review --target-branch main
```

## System Mode Options

There are a number of LG capabilities that are tied not to command line arguments or section configuration, but specifically to additional mode options. That is, they are configured in the `lg-cfg/modes.yaml` file and enabled by specifying the desired mode.

| Option                          | YAML Syntax             | Variants                              | Default | Description                                                                                                                                                                                                                |
|--------------------------------|-------------------------|---------------------------------------|---------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **VCS Modes**                  | `vcs_mode: <variant>`   | `all \| changes \| branch-changes`    | `all`   | Additional file filtering in sections based on version control system status:<br/>- **all** — include all files<br/>- **changes** — include only files changed in the working tree (staged + unstaged + untracked)<br/>- **branch-changes** — include files changed in the current branch relative to the target branch (specified via `--target-branch`) |
| **Markdown Code Fencing**      | `code_fence: <bool>`    | `true \| false`                       | `true`  | Automatic wrapping of code blocks in `fenced` wrappers with language specification (\`\`\`python, \`\`\`bash, etc.)                                                                                           |

<!-- lg:if NOT tag:vcs -->
## Conditional Logic

### Conditions in Markdown Templates

```markdown
## Documentation

{% if tag:docs %}
Detailed API documentation...
{% endif %}

{% if TAGSET:language:python %}
### Python-specific Implementation
${python-impl}
{% endif %}

{% if tag:agent AND NOT tag:minimal %}
### Agent Tools
${agent-tools}
{% endif %}
```

### Conditions in Section Configuration

```yaml
# lg-cfg/sections.yaml
feature-impl:
  extensions: [".py", ".ts", ".js"]
  filters:
    mode: allow
    allow:
      - "/src/feature/**"

    when:
      - condition: "TAGSET:language:python"
        allow:
          - "/src/feature/python/**"
        block:
          - "/src/feature/!(python)/**"

      - condition: "tag:tests"
        allow:
          - "**/*_test.py"
          - "**/*.spec.ts"

  python:
    when:
      - condition: "tag:minimal"
        strip_function_bodies: true
      - condition: "tag:docs_only"
        comment_policy: "keep_doc"
```

### Supported Conditional Operators

- `tag:<name>` - the specified tag is active
- `NOT tag:<name>` - the specified tag is not active
- `tag:<name1> AND tag:<name2>` - both tags are active
- `tag:<name1> OR tag:<name2>` - at least one of the tags is active
- `TAGSET:<set-name>:<tag-name>` - special operator for slices:
  - True if no tag from the set is active
  - True if the specified tag is active
  - False in all other cases

For working with federated scopes, additional operators are added that can be combined with other conditional operators.

- `scope:local` - applies only if rendering from the local scope
- `scope:parent` - applies when rendering from the parent scope

## Setting Modes in Templates

Sometimes it's convenient to forcibly set modes in templates themselves.

```markdown
{% mode dev-stage:development %}
<!-- This is very important architectural code, so it's better to always insert it completely, without narrowing tags -->
<!-- We also guarantee that even during code review, this code will be inserted completely -->
${src-arch}
{% endmode %}

<!-- The rendering of this section fully depends on the mode and/or slices selected by the user in the UI -->
<!-- The user can enable the `vcs_mode` option for this section through modes -->
${src-feature}
```

<!-- lg:comment:start -->
## Complete Template Engine Reference

### Placeholders (main insertion elements)

| Type | Syntax | Examples | Description |
|-----|-----------|---------|----------|
| **Section** (current scope) | `${name}` | `${my-section}` | Insert section from current lg-cfg |
| **Section** (other scope) | `${@origin:name}` | `${@apps/web:web-src}` | Section from another lg-cfg in the repository |
| **Section** (complex path) | `${@[origin]:name}` | `${@[apps/web:v1]:src}` | For paths with colons inside `origin` |
| **Template** (current scope) | `${tpl:name}` | `${tpl:common/intro}` | Template from current lg-cfg |
| **Template** (other scope) | `${tpl@origin:name}` | `${tpl@libs/math:utils}` | Template from another module |
| **Template** (complex path) | `${tpl@[origin]:name}` | `${tpl@[libs/math:v2]:intro}` | For paths with colons |
| **Context** (current scope) | `${ctx:name}` | `${ctx:api/review}` | Context from current lg-cfg |
| **Context** (other scope) | `${ctx@origin:name}` | `${ctx@services/auth:guide}` | Context from another module |
| **Context** (complex path) | `${ctx@[origin]:name}` | `${ctx@[services/auth:v1]:intro}` | For paths with colons |

### Conditional Constructs

| Construct | Syntax | Examples | Description |
|-------------|-----------|---------|----------|
| **If-block** | `{% if condition %}...{% endif %}` | `{% if tag:debug %}...{% endif %}` | Basic conditional construct |
| **If-else** | `{% if condition %}...{% else %}...{% endif %}` | `{% if tag:python %}...{% else %}...{% endif %}` | Condition with alternative |
| **If-elif-else** | `{% if condition1 %}...{% elif condition2 %}...{% else %}...{% endif %}` | `{% if tag:python %}...{% elif tag:javascript %}...{% else %}...{% endif %}` | Chain of conditions |

### Conditional Operators

| Operator | Syntax | Examples | Description |
|----------|-----------|---------|----------|
| **Tag** | `tag:tag_name` | `tag:python`, `tag:docs` | Checks tag activity |
| **Tag Set** | `TAGSET:set:tag` | `TAGSET:language:python` | Special check for tag set slices |
| **Negation** | `NOT condition` | `NOT tag:minimal` | Inverts condition |
| **AND** | `condition1 AND condition2` | `tag:python AND tag:tests` | True if both conditions are true |
| **OR** | `condition1 OR condition2` | `tag:python OR tag:javascript` | True if at least one condition is true |
| **Parentheses** | `(condition)` | `(tag:python OR tag:js) AND tag:tests` | Grouping for priority setting |
| **Scope** | `scope:type` | `scope:local`, `scope:parent` | Check scope type (local/parent) |

### Mode Blocks

| Construct | Syntax | Examples | Description |
|-------------|-----------|---------|----------|
| **Mode Block** | `{% mode set:mode %}...{% endmode %}` | `{% mode dev-stage:review %}...{% endmode %}` | Switches mode for nested content |

### Comments

| Construct | Syntax | Examples | Description |
|-------------|-----------|---------|----------|
| **Template Comment** | `{# text #}` | `{# This won't be in the result #}` | Removed during processing |
| **HTML Comment** | `<!-- text -->` | `<!-- Note -->` | Passes through to final result |
<!-- lg:comment:end -->

---
<!-- lg:raw:start -->
## Using Adaptive Capabilities in the Markdown Adapter

The Markdown adapter also has support for conditional constructs based on HTML comments. This allows using adaptive capabilities in regular Markdown documents without breaking their readability in third-party viewers.

### Conditional Construct Syntax

The syntax is based on special HTML comments with prefixes indicating their role:

#### Conditional Blocks

```markdown
<!-- lg:if tag:python -->
This text will be visible only when the python tag is active.
<!-- lg:endif -->

<!-- lg:if tag:debug -->
Debug information
<!-- lg:else -->
Regular content
<!-- lg:endif -->

<!-- lg:if TAGSET:language:typescript -->
TypeScript-specific content
<!-- lg:elif TAGSET:language:python -->
Python-specific content
<!-- lg:else -->
Content for other languages
<!-- lg:endif -->
```

#### Instruction Comments

```markdown
<!-- lg:comment:start -->
This text WILL BE VISIBLE in Markdown viewers,
but will be excluded during LG tool processing.
<!-- lg:comment:end -->
```

### Usage Example

#### Configuration in YAML

```yaml
docs:
  extensions: [".md"]
  markdown:
    max_heading_level: 2
    enable_templating: true  # Enabling new functionality
    drop:
      sections:
        - match: { kind: text, pattern: "Installation" }
      frontmatter: true
```

#### Example Markdown Document with Conditions

~~~markdown
# API Documentation

## Introduction

This is general API documentation.

<!-- lg:if tag:python -->
## Python Client

```python
import api_client

client = api_client.Client("apikey")
response = client.get_data()
```
<!-- lg:endif -->

<!-- lg:if tag:javascript -->
## JavaScript Client

```javascript
const client = new ApiClient("apikey");
const response = await client.getData();
```
<!-- lg:endif -->

<!-- lg:if tag:debug -->
## Debugging

Debugging information...
<!-- lg:else -->
## Usage

Standard usage instructions...
<!-- lg:endif -->


<!-- lg:comment:start -->
TODO: Add documentation for new API methods
This note won't be included in the final result
<!-- lg:comment:end -->
~~~
<!-- lg:raw:end -->
<!-- lg:endif -->
