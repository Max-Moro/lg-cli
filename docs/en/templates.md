# Listing Generator · Templates, Contexts and Cascading Includes

This section describes how **templating** works in LG: combining `*.ctx.md` (contexts), `*.tpl.md` (templates) and **sections** from `lg-cfg/` — including **targeted includes** from other `lg-cfg` scopes in a monorepo.

## Core Concepts

Before diving into the details, let's clarify the key terms.

### Repository and Scope

**Repository root** is the top-level directory of your project where LG is run from.

**Scope** is any directory that contains its own `lg-cfg/` folder. A scope defines a boundary for configuration and resources.

In simple projects, repository root and scope are the same thing:

```
my-project/           ← repository root = scope
├─ lg-cfg/
│  └─ ...
└─ src/
```

In monorepos, there can be **multiple scopes** — one at the root and several in submodules:

```
monorepo/             ← repository root = root scope
├─ lg-cfg/            ← root scope config
├─ apps/
│  └─ web/            ← nested scope
│     ├─ lg-cfg/      ← web app config
│     └─ src/
└─ libs/
   └─ core/           ← nested scope
      ├─ lg-cfg/      ← core lib config
      └─ src/
```

### Path Resolution: Two Types of Relativity

Paths in LG can be relative in two different ways:

1. **Relative to current directory** (inside `lg-cfg/`):
   - Used for `tpl:`, `ctx:` paths and `md@self:`
   - Changes as you navigate through nested includes
   - Example: from `lg-cfg/docs/intro.ctx.md`, path `../common/header` resolves to `lg-cfg/common/header`

2. **Relative to current scope** (the directory containing `lg-cfg/`):
   - Used for `@origin` references and `md:` without `@`
   - Example: from scope `apps/web`, path `${md:README}` resolves to `apps/web/README.md`

### Accessing Other Scopes

To reference resources from another scope, use the `@origin` syntax:

- `${@apps/web:section}` — section from `apps/web` scope (relative to current scope)
- `${@/:section}` — section from **root scope** (absolute)
- `${tpl@libs/core:intro}` — template from `libs/core` scope

The path after `@` is always relative to the **current scope**, not repository root. Use `@/` to explicitly access the root scope.

---

## What is What

* **Sections** — named sets of files + processing rules (described in `sections.yaml` and `*.sec.yaml`). During rendering they turn into "text inserts".
* **Templates** (`*.tpl.md`) — Markdown fragments where you can insert **sections** and **other templates/contexts**.
* **Contexts** (`*.ctx.md`) — "top-level" documents. You typically feed these to an LLM "as is" (after expanding placeholders).
* **Regular MD** (`*.md`) — any derived Markdown documents not related to the LG tool ecosystem.

---

## What to Store in `lg-cfg/` and How to Organize It

The internal structure is **free-form** — you choose the folders yourself.

Minimum set:

```
lg-cfg/
├─ sections.yaml           # sections file (can be in any subdirectory)
├─ **/*.sec.yaml           # arbitrary number of section fragments (can be in subfolders)
├─ **/*.tpl.md             # templates (fragments)
└─ **/*.ctx.md             # contexts (top-level documents)
```

> **Canonical Section IDs**:
> • For `sections.yaml` files:
>   - `lg-cfg/sections.yaml` → sections have NO prefix (e.g., `docs`, `src`)
>   - `lg-cfg/adapters/sections.yaml` → sections have `adapters/` prefix (e.g., `adapters/src`, `adapters/test`)
> • For `*.sec.yaml` fragments:
>   - if fragment has **exactly one** section → canonical ID = directory prefix + section name
>   - otherwise → `prefix/section` (where `prefix` = fragment path without `.sec.yaml` suffix)
> This allows short references: from `lg-cfg/adapters/overview.ctx.md` you can write `${src}` instead of `${adapters/src}`.

---

<!-- lg:if TAGSET:template-features:common-placeholders -->
## Placeholders and Addressing (Complete Cheat Sheet)

Placeholders support both `${…}` and `$…` (we recommend **braces**). Inside the name, allowed characters are: letters/digits/`_ - / : [ ] . @`.

### Inserting Sections

* Current scope (this `lg-cfg/`):
  `${my-section}`
* From another scope (address relative to **current scope**):
  `${@apps/web:my-section}`
* Root scope (explicit):
  `${@/:my-section}`
* Bracket form, if origin contains colons:
  `${@[apps/web:legacy]:my-section}`

### Inserting Templates

* Local:
  `${tpl:common/intro}`
* From another scope:
  `${tpl@libs/math:docs/guide}`
  `${tpl@[libs/math:v2]:docs/guide}`

### Inserting Context (nested ctx)

* Local:
  `${ctx:api/review}`
* From another scope:
  `${ctx@services/auth:hotfix}`

> **Double path specifier** — this is `origin:resource`:
> `origin` — path to module **relative to current scope** (use `@/` for root scope).
> `resource` — path **inside that `lg-cfg/`** (e.g., `tpl`/`ctx` name or relative path).

---

## Universal Rules via Templates

Templates are the best place for **reusable "framework"** prompts:

```markdown
<!-- lg-cfg/tpl/review.tpl.md -->
# Review Changes

${tpl:intro}  <!-- common introduction -->

## Affected Areas
${@apps/web:web-src}        <!-- section with web sources -->
${@libs/math:math-core}     <!-- section from another package -->

## Checklist
- Architectural consequences?
- Tests and documentation?
```

Then a context "for a specific task" simply assembles the needed blocks:

```markdown
<!-- lg-cfg/ctx/bugfix.ctx.md -->
# Quick Bugfix Review

${tpl:review}
${tests}          <!-- local tests section -->
```

Tips:

* Keep the "common part" (translated phrases, headings, checklists) in `tpl/`.
* At the section level, manage "density" through adapters and `targets` (e.g., cutting function bodies in `pkg/**.py`).
* For "combined" documents, use `max_heading_level` in the Markdown adapter to make the result look smooth.

---

## Cascading Includes Between Scopes (`lg-cfg` of Different Modules)

In a monorepo there are almost always **several** `lg-cfg/` — per module. LG allows **targeted** includes, and other `lg-cfg/` are **lazily** discovered **only if you reference them**.

Examples of addressing:

```markdown
${@apps/web:web-src}               <!-- section from apps/web/lg-cfg/sections.yaml -->
${tpl@libs/math:dev/intro}         <!-- template from libs/math/lg-cfg/dev/intro.tpl.md -->
${ctx@services/auth:hardening}     <!-- context from services/auth/lg-cfg/hardening.ctx.md -->
```

<!-- lg:endif --> <!-- lg:if TAGSET:template-features:task-placeholder -->
## Current Task Placeholder `${task}`

Special placeholder for inserting dynamic description of the current task from the CLI argument `--task`.

### Basic Usage

#### Simple Form

```markdown
## Current Task

${task}
```

**Behavior:**
- If `--task "text"` is passed → text is inserted as is
- If `--task` is not passed → empty string is inserted

**Example command:**
```bash
listing-generator render ctx:dev --task "Implement result caching"
```

**Result:**
```markdown
## Current Task

Implement result caching
```

#### Form with Default Value

```markdown
${task:prompt:"Nothing to do yet. Just confirm that you've read this far."}
```

**Behavior:**
- If `--task` is passed → value from argument is inserted
- If `--task` is not passed → default value from `prompt:` is inserted

**Default Value Syntax:**
- Format: `${task:prompt:"text"}`
- Keyword `prompt:` is required
- Value in double quotes `"`
- Escape sequences supported: `\"`, `\\`, `\n`, `\t`

**Examples:**
```markdown
${task:prompt:"Simple text"}
${task:prompt:"Text with \"quotes\""}
${task:prompt:"Multiline\ntext\nhere"}
```

### Conditional Insertion

You can use the condition `{% if task %}` to include blocks only when a task is present:

```markdown
# Development Context

${tpl:intro}
${src-core}

{% if task %}
## Current Task Description

${task}
{% endif %}
```

### Combining with Other Conditions

```markdown
{% if task AND tag:review %}
## Task for Review

${task}
{% endif %}

{% if NOT task %}
_No specific task specified. General codebase overview._
{% endif %}
```

### Ways to Pass the Task

**Direct string:**
```bash
listing-generator render ctx:dev --task "Implement caching"
```

**Multiline text via stdin:**
```bash
echo -e "Tasks:\n- Fix bug #123\n- Add tests" | listing-generator render ctx:dev --task -
```

**From file:**
```bash
listing-generator render ctx:dev --task @.current-task.txt
```

### Typical Usage Patterns

#### Pattern 1: Always Show Task Section

```markdown
## Current Task

${task:prompt:"General overview without specific task"}
```

#### Pattern 2: Task Section Only When Present

```markdown
{% if task %}
## Current Task

${task}
{% endif %}
```

#### Pattern 3: Different Prompts for Different Modes

```markdown
{% if tag:review %}
${task:prompt:"Conduct code review of changes"}
{% endif %}

{% if tag:debug %}
${task:prompt:"Help find the cause of the bug"}
{% endif %}
```

<!-- lg:endif --> <!-- lg:if TAGSET:template-features:md-placeholders -->
## Inserting Regular Markdown Documents

When composing LG contexts, there is often a need to insert ready-made Markdown documents that were not originally created for LG. Such documents can be inserted in two ways.

Method using a separate section:
```yaml
intro:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/README.md"
```
With this method you can use [all capabilities](markdown.md) of the Markdown language adapter.

There is also a simpler insertion method using the `${md:…}` placeholder:
```markdown
${md:README}
```

> **Note**: The path is relative to the **current scope** directory (the directory containing `lg-cfg/`). In nested includes, the scope changes accordingly.

The `${md:…}` placeholder has quite extensive capabilities.

### Inserting Document from Subdirectory

```markdown
${md:docs/markdown}
```

### Inserting Document Located in `lg-cfg/`

```markdown
${md@self:adapters/gen/LIB_README}
```

### Inserting Document from Another Scope

```markdown
${md@apps/web:web-intro}
```

### Options for Inserting Multiple Paragraphs

The template engine performs contextual analysis of heading levels, so all these options for inserting multiple paragraphs are valid.

**Option 1**

~~~markdown
# Listing Generator

## Extended Documentation

### ${md:docs/templates}

### ${md:docs/markdown}

### ${md:docs/adapters}

## License
~~~

**Option 2**

~~~markdown
# Listing Generator

## Extended Documentation

### Templates, Contexts and Cascading Includes

${md:docs/templates}

### Markdown Guide

${md:docs/markdown}

### Language Adapters

${md:docs/markdown}

## License
~~~

**Option 3**

~~~markdown
# Listing Generator

## Extended Documentation

${md:docs/templates}

${md:docs/markdown}

${md:docs/markdown}

## License
~~~

### Explicit Override of Settings via Parameters

```markdown
${md:docs/templates, level:4, strip_h1:false}
```

This allows users to precisely control behavior in special cases.

### Partial Document Inclusion

```markdown
${md:docs/api#Authentication}
```

Include only a specific documentation paragraph by heading, which is useful for large documents.

### Bulk Documentation Addition and Glob Support

```markdown
${md:docs/guides/*}  <!-- all guides -->
```

### Conditional Includes

```markdown
${md:docs/deployment, if:tag:cloud}
```

Include document based on active tags or tagsets.

<!-- lg:endif --> <!-- lg:if TAGSET:template-features:adaptive -->
## Adaptive Capabilities in Regular Markdown Documents

[More details](adaptability.md#using-adaptive-capabilities-in-markdown-adapter).
<!-- lg:endif -->
