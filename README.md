# Listing Generator

A tool for building dense contexts from source code: traverses projects, filters and normalizes files, then assembles them into a single clean Markdown document — perfect for ChatGPT/Copilot/Gemini/Claude and other LLM assistants.

> In short: you store selection rules in `lg-cfg/` (YAML + context templates), and LG renders "ready-to-paste" text or returns a JSON report with token statistics.

---

## Why and Who Is It For

**Target audience:** developers, team leads, and technical writers who engage in dialogues with AI agents about real code, perform reviews, assign tasks, capture iteration context, while model window size is limited.

**Why:** modern agents work noticeably better when they see **exactly the needed code** with **minimal noise**: no junk from `node_modules/`, logs, generated files, huge binaries, etc. Manual preparation of such context is painful. LG automates:

* selection of relevant files (by filters and extensions),
* light normalization (e.g., Markdown headers, "trivial" `__init__.py`),
* assembly into a single document with **visible file markers**,
* `.gitignore` awareness,
* **`changes` mode** (only modified files),
* **templates and contexts** (section insertions and nested templates),
* size/token estimation and shares ("who's eating the prompt").

There are many ways to form prompts and attach relevant code snippets: from manual copying to context embedding features in IDEs with integrated AI chats. LG differs by doing this **systematically and reproducibly**: rules are stored in the repository, not in your head or AI conversation history.

You describe **what** and **how** goes into the prompt in advance (through sections and templates). This enforces discipline, allows you to "tune" density and **avoid overflowing the model window**, as well as reproduce successful queries through saved templates.

---

## What a "Healthy" AI Agent Workflow Looks Like

1. **Describe rules in the repository**
   Create `lg-cfg/sections.yaml` and additional `*.sec.yaml` as needed. These describe sections (file sets + filters). Use `*.tpl.md` and `*.ctx.md` for templates and contexts.

2. **Build context**
   Render: either a "section" (virtual context of one file set), or a "context" (template that can include multiple sections and other templates).

3. **Iteratively compress**
   Check token statistics (who has the "heaviest share"), move secondary content to separate sections, include on demand. For "small updates" use `--mode changes`.

4. **Save successful prompts**
   Contexts and templates (`*.ctx.md` and `*.tpl.md`) are your "well-working" query formats: reproducible, versionable, with variants for different tasks and agents.

---

## Quick Start

### Installation and Running

Requires Python ≥ 3.10.

Installation:

```bash
# Install from project directory
pip install -e .
```

Verification:

```bash
# Check via module
python -m lg.cli --version

# Or via installed command
listing-generator --version
```

Environment and cache check:

```bash
python -m lg.cli diag
python -m lg.cli diag --rebuild-cache
```

---

## What Goes in `lg-cfg/`

> Important: the configuration directory is always named **`lg-cfg/`**.

Example structure:

```
lg-cfg/
├─ sections.yaml           # sections file (can be in any directory)
├─ additional.sec.yaml     # additional section set (can have many)
├─ intro.tpl.md            # template (can have many, in any subfolders)
├─ onboarding.ctx.md       # context (can have many, in any subfolders)
└─ sub-fold/
   ├─ sections.yaml        # another sections.yaml (sections get sub-fold/ prefix)
   └─ extra.sec.yaml
```

### Sections

* `sections.yaml` — sections file. Can be in `lg-cfg/` root and in any subdirectories.
  - In root: sections without prefix (e.g., `docs`, `src`)
  - In subdirectories: sections with directory prefix (e.g., `adapters/src` from `lg-cfg/adapters/sections.yaml`)
* `*.sec.yaml` — additional section sets (fragments).

A section describes:

* which file extensions to consider,
* allow/block filters over the tree,
* policy for empty files, code-fence, and language adapters.

Minimal example:

```yaml
# Section for project documentation
docs:
  extensions: [".md"]
  markdown:
    # Normalize headings to H2 (outside fenced blocks), remove single H1 at start
    max_heading_level: 2
  filters:
    mode: allow            # default-deny within section
    allow:
      - "/README.md"
      - "/docs/**"

# Core-model submodule sources
core-model-src:
  extensions: [".py", ".md", ".yaml", ".json", ".toml"]
  skip_empty: true
  markdown:
    max_heading_level: 3
  filters:
    mode: allow
    allow:
      - "/core-model/**"
    children:
      core-model:
        mode: block
        block:
          - "**/.pytest_cache/**"
          - "/ROADMAP.md"

# Separate section for roadmap (as text)
core-model-roadmap:
  extensions: [".md"]
  filters:
    mode: allow
    allow:
      - "/core-model/ROADMAP.md"
```

### Filters: How They Work

* Rule tree — **default-allow** (`mode: block`) or **default-deny** (`mode: allow`).
* At each level: first `block`, then (if node is `allow`) — **strict** check against `allow`.
  If `mode: allow` and path doesn't match local `allow`, it's **immediately rejected**.
* `block` is always stronger than `allow`.
* Project's `.gitignore` is respected.
* LG also carefully **doesn't descend** into subtrees that won't yield anything (early pruner).

### Contexts and Templates

* Contexts: `*.ctx.md` (top-level documents).
* Templates: `*.tpl.md` (fragments for insertion).

Example:

```markdown
# Project Introduction

${tpl:intro}

## Core-model module source code

${core-model-src}

## Additional section

${sub-fold/extra/bar}

## Current task

${task}
```

Sections from root `lg-cfg/sections.yaml` are accessible directly (`${docs}`).
Sections from subdirectory `sections.yaml` files have directory prefix (e.g., `${adapters/src}` from `lg-cfg/adapters/sections.yaml`).
Fragments use hierarchical paths: file `sub-fold/extra.sec.yaml` → section `bar` → `${sub-fold/extra/bar}`.

**Context-dependent references**: From templates in subdirectories, you can use short names.
Example: from `lg-cfg/adapters/overview.ctx.md` you can write `${src}` and it will resolve to `adapters/src`.

Special placeholder `${task}` inserts text from `--task` argument:
* `${task}` — simple insertion (empty string if not specified)
* `${task:prompt:"default text"}` — with default value
* `{% if task %}...{% endif %}` — conditional block insertion

*More details:* [templates.md](docs/en/templates.md).

---

## Language Adapters

Listing Generator uses adapters for different languages and formats. They help "optimize" listings: remove junk, normalize headings, filter paragraphs, or even strip function bodies leaving only signatures. Adapter settings are specified right in section YAML — globally for the section or targeted to specific paths via `targets`.

### Configuration Example

```yaml
core:
  extensions: [".py", ".md"]
  skip_empty: true

  # Global rules for entire section
  python:
    strip_function_bodies: false

  markdown:
    max_heading_level: 2

  # Local overrides for specific folders and files
  targets:
    - match: "/pkg/**.py"
      python:
        strip_function_bodies: true      # only signatures in this folder

    - match: ["/docs/**.md", "/notes/*.md"]
      markdown:
        drop:
          sections:
            - match: { kind: regex, pattern: "^(License|Changelog|Contributing)$", flags: "i" }
```

In this example, the `core` section describes two languages. For Python, stripping function bodies is globally disabled, but inside the `/pkg/` folder it's enabled. For Markdown, a general heading level is set, but in `/docs/` and `/notes/` paragraphs will additionally be filtered by specified patterns.

The `match` key accepts either a string or a list of glob patterns. When multiple rules match, the more specific (longer and more concrete) one wins; if equal — the later one in the list. This allows neatly layering local "overrides" on top of section settings.

Separate empty file policy (`skip_empty` at section level and `empty_policy` in adapters) works as if it's part of language options: the section sets the general strategy, and the adapter can refine it if needed. Possible values: `empty_policy: inherit|include|exclude`.

---

### Available Adapters

#### Markdown

* Normalize headings (remove lone H1, shift levels).
* Systematically **drop entire sections** by headings (with subtree).
* Remove **YAML front matter** at the beginning.
* Insert **placeholders** in place of removed content (optionally).

*More details:* [markdown.md](docs/en/markdown.md).

#### Programming Languages

*More details:* [adapters.md](docs/en/adapters.md).

---

## Token Statistics

To facilitate the process of optimizing listings and contexts, LG provides a summary report on token usage.

LG supports several open-source tokenization libraries (tiktoken, tokenizers, sentencepiece) and requires explicit specification of tokenization parameters on each run.

*More details:* [tokenizers.md](docs/en/tokenizers.md).

---

## Adaptive Capabilities

All methods for creating universal templates and section configurations are described in the [Adaptive Capabilities](docs/en/adaptability.md) section.
<!-- lg:comment:start -->
---

## CLI Options

General format:

```bash
listing-generator <command> <target> [--mode MODESET:MODE] [--tags TAG1,TAG2] [<additional_flags>]

# For render/report, tokenization parameters are required:
listing-generator render|report <target> \
  --lib <tiktoken|tokenizers|sentencepiece> \
  --encoder <encoder_name> \
  --ctx-limit <tokens>
```

Where `<target>`:

* `ctx:<name>` — takes file `lg-cfg/<name>.ctx.md` (subfolders supported).
* `sec:<id>` — virtual context of a single section (canonical ID).
* `<name>` — searches first as `ctx:<name>`, otherwise as `sec:<id>`.

Commands:

* `render` — output **final text only** (Markdown).
* `report` — **JSON report** (format v5): statistics, files, context block.
* `list contexts|sections|tokenizer-libs|encoders` — list available entities (JSON).
* `diag` — environment/cache/config diagnostics (JSON), has `--rebuild-cache`.

Tokenization parameters:

* `--lib` — tokenization library (`tiktoken`, `tokenizers`, `sentencepiece`)
* `--encoder` — encoder/model name (e.g.: `cl100k_base`, `gpt2`, `google/gemma-2-2b`)
* `--ctx-limit` — context window size in tokens (e.g.: `128000`, `200000`)

Examples:

```bash
# Render context from template with tokenization for GPT-4
listing-generator render ctx:onboarding \
  --lib tiktoken \
  --encoder cl100k_base \
  --ctx-limit 128000 > prompt.md

# Render "section only" (no template)
listing-generator render sec:core-model-src \
  --lib tiktoken \
  --encoder cl100k_base \
  --ctx-limit 128000 > prompt.md

# Same but only changed files in working tree
listing-generator render ctx:onboarding \
  --lib tiktoken \
  --encoder cl100k_base \
  --ctx-limit 128000 \
  --mode vcs:branch-changes > prompt.md

# JSON report with token stats for GPT-4o
listing-generator report ctx:onboarding \
  --lib tiktoken \
  --encoder o200k_base \
  --ctx-limit 200000 > report.json

# Report for Gemini using sentencepiece
listing-generator report ctx:onboarding \
  --lib sentencepiece \
  --encoder google/gemma-2-2b \
  --ctx-limit 1000000 > report.json

# Render context with current task description
listing-generator render ctx:dev \
  --lib tiktoken --encoder cl100k_base --ctx-limit 128000 \
  --task "Implement result caching"

# Multi-line task via stdin
echo -e "Tasks:\n- Fix bug #123\n- Add tests" | \
  listing-generator render ctx:dev --lib tiktoken --encoder cl100k_base --ctx-limit 128000 --task -

# Task from file
listing-generator render ctx:dev \
  --lib tiktoken --encoder cl100k_base --ctx-limit 128000 \
  --task @.current-task.txt

# Diagnostics
listing-generator diag
listing-generator diag --rebuild-cache

# Lists
listing-generator list contexts
listing-generator list sections
listing-generator list tokenizer-libs
listing-generator list encoders --lib tiktoken
listing-generator list encoders --lib tokenizers
```

---

## How LG Renders Documents

* If **all files are Markdown/plain text**, LG simply concatenates their content.
* Otherwise:

  * **with code-fence** (default): blocks by languages, grouped **in order of occurrence**;
    inside each block — file marker `# —— FILE: path ——`, then content.
  * **without code-fence**: linear document with marker before each file.

This makes the prompt **readable** for humans and convenient for agents: it's clear where each fragment comes from.

---

## Cache and Performance

LG uses file cache `.lg-cache`:

* **Processed cache** — adapter results + their metadata.
* **Raw/Processed tokens** — saved token counts (by model/mode).
* **Rendered tokens** — count of final document ("with glue") and "sections-only".

Cache keys consider tool version, file fingerprint, adapter config, group composition, etc.
Management: `listing-generator diag`, `listing-generator diag --rebuild-cache`. Can disable cache via `LG_CACHE=0`.

---

## Practical Tips for "Dense" Contexts

* **Keep sections small and thematic.** Better several sections than one "everything about everything".
* **Strict `allow` nodes** use where full content predictability is needed.
* **Markdown templates** apply as prompt "frame": brief intro, tasks, section placeholders.
* **`changes` mode** — best friend for patch iterations and code review via LLM.
* **Watch shares** (`promptShare`/`ctxShare`) in `report`: helps distribute "holding cost".
* **Normalize headings** (`max_heading_level`) — makes reading long contexts easier.
* **Don't drag secrets.** Configure `block` for artifacts/keys/secrets/binaries.

---

## IDE/Plugin Integration

In most cases you'll run LG **through integration** (VS Code / JetBrains, etc.).
Nevertheless, **all selection/template logic lives in the repository** (`lg-cfg/`), so:

* reviewing and evolving rules is simple (via PRs),
* transferring successful prompts between projects — trivial,
* same configuration works in CLI and IDE.

---

## License

Listing Generator is licensed under the Apache License, Version 2.0.  
See the `LICENSE` file for the full license text.
<!-- lg:comment:end -->