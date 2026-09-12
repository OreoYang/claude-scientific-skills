---
name: pretty-mermaid
description: >-
  Renders Mermaid diagrams as SVG via official mermaid.js (mermaid.ink / mermaid.live).
  No beautiful-mermaid, no Chrome, no Puppeteer. Use when rendering .mmd files,
  publishing Confluence pages with ```mermaid blocks, or matching mermaid.live output.
version: 2.0.0
---

# Pretty Mermaid

**Skill root:** `~/.cursor/skills/pretty-mermaid/` (personal Cursor skill; real files, not a symlink).

Render **official mermaid.js** SVG — the same engine as [mermaid.live](https://mermaid.live). Uses **mermaid.ink** over HTTPS (Kroki as fallback). No `mmdc`, no Puppeteer, no beautiful-mermaid.

## Confluence publish

Wiki pages with ` ```mermaid ` blocks: use **`confluence/publish.py`** + a repo-side `*.publish.json` (content stays in the project; scripts live in this skill). Full guide: `references/CONFLUENCE.md`.

```bash
python3 ~/.cursor/skills/pretty-mermaid/confluence/publish.py \
  --config path/to/page.publish.json
```

`publish.py` calls `confluence/mermaid.py` → mermaid.ink. CLI `scripts/render.mjs` uses the same official renderer.

**New pages:** create empty page in Confluence UI first; then `publish.py`. Content layout: `references/PAGE_TEMPLATE.md`. Publish mechanics: `references/CONFLUENCE.md`.

## Quick Start

### Render a Single Diagram

```bash
python3 ~/.cursor/skills/pretty-mermaid/confluence/mermaid.py render \
  diagram.mmd diagram.svg --theme default
```

Or Node:

```bash
node ~/.cursor/skills/pretty-mermaid/scripts/render.mjs \
  --input diagram.mmd \
  --output diagram.svg \
  --theme default
```

### Batch Render Multiple Diagrams

```bash
node ~/.cursor/skills/pretty-mermaid/scripts/batch.mjs \
  --input-dir ./diagrams \
  --output-dir ./output \
  --theme default \
  --workers 4
```

---

## Workflow Decision Tree

**Step 1: What does the user want?**
- **Render existing Mermaid code** → [Rendering](#rendering-diagrams)
- **Create new diagram** → [Creating](#creating-diagrams)
- **Apply/change theme** → [Theming](#theming)
- **Batch process** → [Batch Rendering](#batch-rendering)

**Step 2: Output format**
- **SVG** only (`--format svg`). ASCII Mermaid (beautiful-mermaid) has been removed; preview on mermaid.live or render SVG.

**Step 3: Select theme** (official mermaid.js)
- **Light docs / Confluence** → `default` (same as mermaid.live)
- **Dark docs** → `dark`
- **Also:** `forest`, `neutral`, `base`
- **See all** → `node ~/.cursor/skills/pretty-mermaid/scripts/themes.mjs`

Legacy names (`github-light`, `tokyo-night`, `dracula`, …) map to `default` or `dark`.

---

## Rendering Diagrams

### From File

1. Save Mermaid source to a `.mmd` file (or use a ` ```mermaid ` block in Markdown).
2. Render:

```bash
node ~/.cursor/skills/pretty-mermaid/scripts/render.mjs \
  --input diagram.mmd \
  --output diagram.svg \
  --theme default
```

3. Verify: open the SVG, or paste the `.mmd` into https://mermaid.live/ — they should match.

### Output Formats

**SVG** — web, Confluence, docs. Official mermaid.js look (`classDef`, `<br/>` in labels, rounded nodes).

**ASCII** — removed. Use mermaid.live or SVG. (Fixed-width **box-drawing** diagrams for Confluence still live in `confluence/ascii_art.py` — that is not Mermaid.)

### Options

```bash
node ~/.cursor/skills/pretty-mermaid/scripts/render.mjs \
  --input diagram.mmd \
  --theme default \
  --transparent \
  --output diagram.svg
```

`%%{init: ...}%%` in the source is left as-is (not overwritten).

---

## Creating Diagrams

### Using Templates

```bash
ls ~/.cursor/skills/pretty-mermaid/assets/example_diagrams/
# flowchart.mmd  sequence.mmd  state.mmd  class.mmd  er.mmd
```

Copy, edit, render with `--theme default`. Syntax: [DIAGRAM_TYPES.md](references/DIAGRAM_TYPES.md). Preview on mermaid.live before publish.

### From User Requirements

Process/workflow → Flowchart · API/interaction → Sequence · States → State · Object model → Class · Database → ER.

---

## Theming

```bash
node ~/.cursor/skills/pretty-mermaid/scripts/themes.mjs
```

Official themes: `default`, `dark`, `forest`, `neutral`, `base`. Details: [THEMES.md](references/THEMES.md).

Confluence technical pages should use **`default`** so figures match mermaid.live.

---

## Batch Rendering

```bash
node ~/.cursor/skills/pretty-mermaid/scripts/batch.mjs \
  --input-dir ./diagrams \
  --output-dir ./rendered \
  --theme default \
  --workers 4
```

Needs network (mermaid.ink). `--workers` is parallel HTTP fetches.

---

## Troubleshooting

### Network / mermaid.ink error

Renderer fetches `https://mermaid.ink/svg/<base64url>`. Override with `MERMAID_INK_URL`. Kroki (`https://kroki.io/mermaid/svg`) is the fallback.

Paste the `.mmd` into https://mermaid.live/ to confirm syntax.

### Invalid Mermaid Syntax

Validate on mermaid.live. Common issues: missing spaces in `A --> B`, unclosed brackets, bad `classDef`.

### Empty labels in Confluence

Official mermaid.js SVG uses `<foreignObject>` for some labels. If Confluence strips them, fall back to mermaid.ink PNG (`/img/` instead of `/svg/`) — only if SVG text is blank on the wiki.

---

## Resources

### scripts/
- `official-mermaid.mjs` — mermaid.ink / Kroki fetch (shared)
- `render.mjs` — single-file CLI
- `batch.mjs` — directory of `.mmd`
- `themes.mjs` — list official themes + aliases

### confluence/
- `mermaid.py` — official SVG render + Confluence image/expand macros
- `publish.py` — Markdown → storage HTML → wiki
- `page.py` — full-width
- `ascii_art.py` — box-drawing (not Mermaid)

### references/
- `PAGE_TEMPLATE.md`, `CONFLUENCE.md`, `THEMES.md`, `DIAGRAM_TYPES.md`, `api_reference.md`

---

## Tips

- Author as you would on mermaid.live (`<br/>`, `classDef`, subgraphs).
- Keep diagrams under ~50 nodes; split the rest to a child page.
- Confluence: always SVG attachment + expand with the same source as `.md`.
