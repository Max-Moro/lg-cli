# Listing Generator · Markdown Guide

This document describes **all Markdown adapter features** in Listing Generator (LG): heading normalization, removal of noisy sections (by headings and paths), front matter handling, and practices for building compact prompts.

---

## Why This Is Needed

LLM models respond noticeably better when they:
- see **structured Markdown** (correct heading levels),
- don't receive **noise** (installation/licenses/outdated content),
- context **fits within the model's window**.

The Markdown adapter helps:
1) Normalize headings (remove lone H1, shift levels).
2) Systematically **remove entire sections** by headings (with subtrees).
3) Remove **YAML front matter** at the beginning.
4) Insert **placeholders** in place of removed content (optional).

> ⚠️ Section removal by headings occurs **outside fenced code**. Content within ```code blocks``` is never analyzed as Markdown structure.

---

## Quick Start: Minimal Configuration

### Drop Mode — Removing Specified Content

```yaml
# lg-cfg/config.yaml (fragment)
docs:
  extensions: [".md"]
  markdown:
    # 1) Heading normalization
    max_heading_level: 2   # highest level in resulting document → H2

    # 2) What to remove (and why)
    drop:
      sections:
        - match: { kind: text, pattern: "Installation" }   # remove entire "Installation" section
          level_at_most: 3
          reason: "user-facing install guide"
        - match: { kind: slug, pattern: "^cli-options$" }  # by slug, stable to punctuation/case
        - match: { kind: regex, pattern: "^(Legacy|Deprecated)", flags: "i" }
        - path: ["FAQ", "User"]                            # branch by parents → remove subtree

      frontmatter: true  # remove YAML front matter (--- ... ---) at the beginning

    # 3) How to mark omissions
    placeholder:
      mode: summary      # none|summary
      template: "> *(Section «{title}» omitted; −{lines} lines)*"
```

### Keep Mode — Preserving Only Specified Content

```yaml
# lg-cfg/config.yaml (fragment)
docs:
  extensions: [".md"]
  markdown:
    # 1) Heading normalization
    max_heading_level: 2   # highest level in resulting document → H2

    # 2) What to keep (inverse of drop logic)
    keep:
      sections:
        - match: { kind: text, pattern: "Usage" }          # keep only "Usage" section
        - match: { kind: slug, pattern: "api-reference" }  # and API reference
        - match: { kind: regex, pattern: "^Important", flags: "i" }  # and important sections

      frontmatter: true  # preserve YAML front matter (--- ... ---)

    # 3) In keep mode, placeholders are not used — removed content simply disappears
```

> ⚠️ **Important**: `drop` and `keep` modes are mutually exclusive — cannot be used simultaneously.

---

## How It Works

### Order of Operations (Pipeline)

1. **Parsing** Markdown:

   * detecting fenced blocks (\`\`\`/\~\~\~) and their boundaries;
   * **ATX** headings (`#..######`) and **Setext** headings (underlines `===` / `---`);
   * section tree: `title`, `level`, subtree boundary.

2. **Forming removal intervals**:

   * `drop.sections`: entire subtrees by `text|slug|regex|path` rules;
   * `frontmatter`: YAML header at the beginning ("--- … ---").

3. **Merging overlaps** → unified set of intervals.

4. **Transformation**:

   * remove intervals;
   * insert brief placeholders with data (title, number of lines/bytes) according to `placeholder` policy.

5. **Heading normalization**:

   * if `strip_h1=true` → remove top **H1** (ATX or Setext);
   * then shift levels so that the top one becomes `max_heading_level`

> 💡 Normalization is performed **after** removal, so levels are correct in the "stitched" prompt.

---

## Configuration Reference

### `markdown` Key

| Field               | Type      | Default | Description                                                                                        |
|---------------------|-----------|---------|---------------------------------------------------------------------------------------------------|
| `max_heading_level` | int\|null | null    | If set — shifts heading levels (outside fenced), so the minimum becomes equal to this value.      |
| `strip_h1`          | bool      | false   | Removes top H1 (ATX or setext).                                                                   |
| `drop`              | object    | —       | Removal settings (mutually exclusive with `keep`).                                                |
| `keep`              | object    | —       | Content preservation settings (mutually exclusive with `drop`).                                   |
| `placeholder`       | object    | —       | Placeholder policy for removed blocks (only for `drop` mode).                                     |

---

### `drop.sections[]` — Removal by Headings

Each element is **one rule** that selects 0..N sections (with subtrees):

```yaml
drop:
  sections:
    - match: { kind: text|slug|regex, pattern: "<string>" , flags: "ims" }  # one of match modes
      path:  ["Parent A", "Parent B"]     # (opt.) limit by parent context
      level_at_least: 1                   # (opt.) filter by heading level
      level_at_most:  3
      level_exact:    2
      reason: "legacy docs"               # (opt.) will appear in report metadata
      placeholder: "> *(Section «{title}» omitted)*"  # (opt.) override global template
```

* `kind: text` — exact comparison of `title` (without formatting).
* `kind: slug` — comparison by **slug** (GitHub-style): lowercase, spaces→hyphens, punctuation removed.
  Examples:
  `"CLI Options & Flags" → "cli-options-flags"`,
  `"FAQ: User" → "faq-user"`.
* `kind: regex` — regular expression on `title`. `flags` — string of `i m s` (ignorecase, multiline, dotall).
* `path` — list of **exact** ancestor headings. Useful when identical names appear in different branches.

> Example: remove only "Deprecated" **inside** "API / v1":
>
> ```yaml
> - path:  ["API", "v1"]
>   match: { kind: text, pattern: "Deprecated" }
> ```

---

### `keep.sections[]` — Preserving Only Specified Sections

**Keep mode** works **inversely** to drop mode: specifies which sections to **keep**, everything else is removed.

```yaml
keep:
  sections:
    - match: { kind: text|slug|regex, pattern: "<string>", flags: "ims" }  # one of match modes
      path:  ["Parent A", "Parent B"]     # (opt.) limit by parent context
      level_at_least: 1                   # (opt.) filter by heading level
      level_at_most:  3
      level_exact:    2
      reason: "important content"         # (opt.) will appear in report metadata
      # placeholder NOT supported — removed content simply disappears
```

All selectors work exactly the same as in `drop` mode:

* `kind: text` — exact heading comparison.
* `kind: slug` — comparison by GitHub slug.
* `kind: regex` — regular expression.
* `path` — limitation by parent chain.

> **Important differences of keep mode:**
>
> * **Placeholders are not inserted** — removed content simply disappears.
> * **Subtrees are preserved** — when preserving an H2 section, all its H3, H4, etc. subsections are preserved.
> * **Empty list** `sections: []` will remove all content (except frontmatter if `frontmatter: true`).

> Example: keep only "Usage" and "API Reference":
>
> ```yaml
> keep:
>   sections:
>     - match: { kind: text, pattern: "Usage" }
>     - match: { kind: slug, pattern: "api-reference" }
> ```

### `drop.frontmatter` — Removing YAML Front Matter

```yaml
drop:
  frontmatter: true
```

If the document starts with a `---` line, everything up to the next `---` line outside fenced code will be removed.

> Specifically YAML-style `---` is supported. TOML variant `+++` is not processed.

---

### `placeholder` — How to Mark "Omissions"

```yaml
placeholder:
  mode: none | summary
  template: "> *(Section «{title}» omitted; −{lines} lines)*"
```

* `mode: none` — simply remove.
* `mode: summary` — insert string according to `template`.
* Available variables: `{title}`, `{level}`, `{lines}`, `{bytes}`.
* Per-rule you can override the template in the rule itself `sections[].placeholder`.

---

## Heading Normalization

* **Removing H1**: if `strip_h1: true` is set in the section configuration and the first line is `# ...` (or a Setext heading), the heading is removed to avoid creating "second H1s" in combined contexts.
* **Level shifting**: if `max_heading_level` is specified, heading levels **outside fenced code** are shifted so that the top one becomes exactly this level (usually `2`).

This is important when **building through templates** (`lg-cfg/contexts/*.tpl.md`): when you insert multiple sections, headings maintain correct hierarchy, and the model "sees" the structure.

---

## Recipes

### Remove Installation, CLI, and License

```yaml
docs:
  extensions: [".md"]
  markdown:
    max_heading_level: 2
    drop:
      sections:
        - match: { kind: text, pattern: "Installation" }
        - match: { kind: slug, pattern: "^cli" }          # CLI, CLI Options, CLI Usage…
        - match: { kind: regex, pattern: "^License$", flags: "i" }
    placeholder:
      mode: summary
      template: "> *(Omitted «{title}»)*"
```

### Align Heading Levels When Stitching Sections

```yaml
guides:
  extensions: [".md"]
  markdown:
    max_heading_level: 2   # In final document, top headings → H2
```

Template:

```markdown
# Guide

${tpl:intro}      <!-- nested template -->
${guides}         <!-- Markdown section -->
${tpl:appendix}
```

### Targeted Rules via `targets`

Remove "License" **only** in `docs/**.md`, without touching `LICENSE.md`:

```yaml
docs:
  extensions: [".md"]
  targets:
    - match: "/docs/**.md"
      markdown:
        drop:
          sections:
            - match: { kind: text, pattern: "License" }
```

### Comparison of Drop vs Keep Modes

**Drop mode** is better when you need to **remove individual noise**:
- Remove installation from developer documentation
- Exclude deprecated API from reference
- Remove user-facing content from technical docs

**Keep mode** is more efficient when you need to **significantly reduce** content:
- Keep only Usage from long README
- Extract only API Reference from complex documentation
- Preserve only key sections from large instructions

---

## Diagnostics and Reports

Command:

```bash
listing-generator report ctx:my-context --model gpt-4o > report.json
```

In `files[].meta` for Markdown files, the following fields will appear:

* `md.mode` — used mode: `"drop"` or `"keep"`.
* `md.removed.sections` — number of removed/processed sections.
* `md.removed.frontmatter` — `true/false`.
* `md.placeholders` — how many placeholders were inserted (only in drop mode).

This helps understand what "eats" tokens and which rules actually worked.

---

## Limitations and Default Behavior

* **Fenced code**: headings inside \`\`\`/\~\~\~ are ignored as structure.
* **Blockquote headings** (`> # Heading`) are not considered structural headings for section removal.
* **Setext** is supported for H1 (`===`) and H2 (`---`) levels — as in CommonMark.
* **Front matter** is only recognized in YAML-style `---`.
* **Regular expressions** — standard Python regex (not PCRE). For most tasks, `i` (ignorecase) is sufficient.
* If `max_heading_level` is not set — levels are not shifted.
* H1 removal only occurs if the `strip_h1: true` flag is explicitly set in the section configuration.
