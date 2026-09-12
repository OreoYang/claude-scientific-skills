# Confluence technical page template

Use this layout when **creating** or **rewriting** architecture / technical-guide wiki pages.
Default to **concise and scannable** — link or child-page the deep dive; do not paste everything on one page.
Write in **simple English**: short sentences, one idea each, common words, active voice. Page owners are often not native speakers and must defend the text in review. Code identifiers, YANG keywords and numbers stay exact — simplify only the prose around them.

**Reference example (Vecima):** [Technical Guide: XGS Node QoS — BAL, Upstream & Downstream (R26.1.0)](https://vecima.atlassian.net/wiki/spaces/~fjyang/pages/234751290) — clear Parts, one diagram per major idea, tables for facts, short code snippets, entry-point tables at section ends.

---

## Page skeleton

```text
Title (specific: topic + scope + version/release if relevant)

Opening paragraph (2–4 sentences)
  → what problem / who reads this / what changed vs prior release

Part 1 — Fundamentals
---------------------
### 1.1 What problem does … solve?
    [figure: topology or object model]
    • 3–5 bullet takeaways (enqueue / schedule / shape — not essay)

### 1.2 Core objects (or components)
    | Name | Role |
    | table, one row per concept |

### 1.3 … (mechanism, comparison, or rates)
    short prose + table OR code macro (≤15 lines)

### 1.x Glossary (optional, end of Part 1)
    | Term | Meaning |

---

Part 2 — Path / domain A
------------------------
### 2.1 Why A differs from B
    | Concern | A | B |   ← comparison table before detail

### 2.2 Topology
    [one figure]

### 2.3–2.6 Steps, packet path, boot sequence (as needed)
    numbered lists or short subsections — not duplicate figures

### 2.x Key code entry points
    | Step | File | Symbol / region |

---

Part 3 — Path / domain B (+ history if needed)
----------------------------------------------
### 3.1 Current mechanism
#### 3.1.1 … (nested only when Part is large)

### 3.2 History / rationale (optional Part)
    ticket → symptom → fix table; before vs after table

### 3.3 Resources / limits (optional)
    | Limit | Value | Source |

Part 4 — Future / requirements (optional)
```

**Heading rules**

| Level | Use |
|-------|-----|
| Page title | `h1` once — Confluence page title |
| Part | `h2` with em dash title, or `h2` + horizontal rule (QoS style) |
| Section | `h3` — `N.M Title` numbering (`1.1`, `2.3`) |
| Sub-detail | `h4` only when Part 3+ is long |

TOC macro (`minLevel=2`, `maxLevel=3`) goes **first in the body**, above the opening paragraph and any `h1`. Do not rely on TOC alone for structure — Parts and `N.M` numbers must read clearly in View.

---

## Figure budget (avoid “diagram sprawl”)

| Page type | Target |
|-----------|--------|
| Technical guide (QoS-style) | **1 figure per Part** (or per major path); draw.io or Mermaid |
| Architecture overview | **1 overview** + up to **2–3** domain figures — not one diagram per `h3` |
| Mutex / lock inventory | tables primary; 0–1 overview figure |

**Mermaid pages (pretty-mermaid publish)**

- Repo `.md`: prefer **few ` ```mermaid ` blocks** with clear Part-level placement.
- Each published block → SVG + optional expand for source — **not** mandatory under every subsection.
- Split extra diagrams to a **child page** (“Detailed call flows”) when the parent exceeds ~4 figures.

---

## Tables (preferred over prose)

| Use table for | Avoid |
|---------------|--------|
| Object / API fields | Long bullet lists of field meanings |
| US vs DS / before vs after | Repeated paragraphs comparing two sides |
| Limits, constants, ticket mapping | Inline wall of `#define` values |
| Code entry points | Narrative “see `foo.c` around line …” only |

Keep tables **≤8 columns**; use `data-layout="wide"` on full-width pages.

---

## Code on the page

- **Architecture / technical guide:** short API/config snippets in `code` macros (`wide` layout for struct dumps). ≤~15 lines.
- **Debug / runbook / how-to:** each step states **what it does** (1–2 sentences + pass); the **actual script** goes in a collapsed Expand wrapping a `code` block — never an open script wall and never a comment-only stub. MCP HTML: `<details><summary>Script — …</summary><pre><code>…</code></pre></details>`. Example: [CPMP Kafka E2E Debug](https://vecima.atlassian.net/wiki/spaces/~Oreo.Yang/pages/265487660).
- **No** repo maintainer commands (`bitbake`, `publish.py`, `gen-*-svg`) in wiki body — repo only (`<!-- publish:skip -->` in `.md`).
- **No** paste-guide markdown (`*.paste.md`) content on the wiki — those are UI helper drafts.

---

## `intro.html` pattern (repo)

Minimal header before scripted sections:

```html
<ac:structured-macro ac:name="toc" ac:schema-version="1">
  <ac:parameter ac:name="maxLevel">3</ac:parameter>
  <ac:parameter ac:name="minLevel">2</ac:parameter>
</ac:structured-macro>
<h1>Page title</h1>
<p><strong>JIRA:</strong> <a href="…">KEY</a><br/>
<strong>Related:</strong> <a href="…">parent overview</a><br/>
<strong>Repo source:</strong> <code>path/to/confluence-*.md</code></p>
<hr/>
```

Body sections follow from `.md` or UI-edited prefix. Do not duplicate the full page in `intro.html`.

---

## Anti-patterns (“too much detail”)

| Anti-pattern | Prefer |
|--------------|--------|
| 8–16 Mermaid diagrams on one page | 1 overview + link child page for per-domain detail |
| Every `h3` has expand + 100-line mermaid source | Figure visible; expand only where reviewers edit source |
| Fragment HTML splice + API merge | UI intro + `preserve_before_heading` + `publish.py` for diagram sections |
| Full sequence diagrams for static structure | Flowchart / draw.io for topology; sequence only for real message flow |
| Duplicate “overview” + “simplified” + “legacy” figures | One current diagram; history in prose/table |
| Actor-level swimlane per file | One dispatch figure + entry-point table |
| Paste tables copied from design drafts | Trim to columns readers need (Path \| Caller \| Notes) |
| “Figures are Archify SVG locked to light + classic” in the intro | Theme lock is the exporter; wiki intro is scope only |

When **updating** an over-long page: collapse duplicate figures, move deep sections to child pages, keep Part structure and entry-point tables.

---

## New page workflow (summary)

1. Confluence UI: create empty page → full-width.
2. Repo: `confluence-*.md` following skeleton above; `intro.html` + `*.publish.json`.
3. `publish.py --dry-run` → check SVGs match mermaid.live.
4. First publish: diagram sections via `publish.py`; intro/prose via UI if mixed page (`preserve_before_heading`).
5. Open **Edit** once; verify structure matches template, not raw dump.

See `CONFLUENCE.md` for publish mechanics and safe API patterns.
