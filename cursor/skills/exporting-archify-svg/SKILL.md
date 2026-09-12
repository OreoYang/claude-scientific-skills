---
name: exporting-archify-svg
description: >-
  Use when exporting an Archify HTML diagram to SVG for Confluence or wiki,
  composing a full-page figure (title + diagram + cards), matching viewer
  light+classic colors, or when a generated SVG does not match Archify
  Export → SVG.
---

# Exporting Archify SVG

**Skill root:** `~/.cursor/skills/exporting-archify-svg/`

Turn a **delivered Archify HTML** into wiki-ready SVG that uses the same stylesheet as the viewer's Export → SVG, then lock **light + classic** so Confluence always matches the on-screen look.

**REQUIRED SUB-SKILL:** Archify (author + `deliver` the HTML first). This skill does not draw topology.

**Not this skill:** Mermaid / ` ```mermaid ` wiki figures → pretty-mermaid.

## Default

| Knob | Wiki default | Change only when asked |
|---|---|---|
| Color mode | `light` | `--theme dark` |
| Visual preset | `classic` | `--preset signal-flow\|blueprint\|editorial` |
| Attachment | `*.page.svg` (title + diagram + cards) | `--diagram-only` for the middle map alone |

English copy is an Archify authoring default, not this exporter.

## Workflow

1. Deliver HTML with Archify (`validate` then `deliver`). Do not export from a failed or stale HTML.
2. Run the compositor (do **not** scrape the inner `<svg>` and hand-copy CSS):

```bash
node ~/.cursor/skills/exporting-archify-svg/scripts/compose-page-svg.mjs \
  path/to/delivered.html
```

Writes next to the HTML:

- `*.diagram.svg` — middle map, serializeSvg stylesheet, theme locked
- `*.page.svg` — title + diagram + info cards, no toolbar

3. Open `*.page.svg` locally before wiki upload. Confirm node fills, masks, and sigils match the HTML viewer at Light + Classic.
4. If the user asked for Confluence, publish `*.page.svg` (see below).

`--help` lists flags. `--out-dir` / `--stem` rename outputs.

## Why not Export → SVG / a hand-copied SVG

Archify **Export → SVG** serializes **only** `.diagram-container svg` (`serializeSvg(1, { autoTheme: true })`). Title, toolbar, and cards are HTML and are omitted. `autoTheme` defaults to **dark** and switches light via `prefers-color-scheme`, so a wiki `<img>` can disagree with the Light toggle the user had on screen.

A hand-copied inner SVG plus a short `--frontend-fill` token list is **not** an export: it drops `.c-mask`, `.t-primary`, `.semantic-sigil`, and the official `.c-region` rule, so colors will not match.

This script copies the same SVG-only CSS filter as `serializeSvg`, then writes locked theme variables **after** that host stylesheet (same cascade as the viewer's raster path).

## Confluence

Wiki pages with Mermaid stay on pretty-mermaid. Archify figures are an **SVG attachment**.

1. `confluence_get_page` with `convert_to_markdown=false`. Keep any `toc` macro. Record version.
2. `confluence_upload_attachment` of `*.page.svg` (same filename → new version).
3. Storage HTML, not markdown (markdown drops macros). One intro paragraph + image. The intro is **scope only** (problem, audience, what the figure shows). Do **not** mention Archify, mermaid.ink, `light + classic`, theme lock, or how the SVG was exported — that is exporter machinery, not page content.

```xml
<p>…short scope…</p>
<p><ac:image ac:align="center" ac:layout="wide">
  <ri:attachment ri:filename="stem.page.svg" />
</ac:image></p>
```

4. `page_width: full-width`. Do not cap `ac:width` small. `version_comment` is a short content reason (what changed on the page), not a renderer note.
5. Re-fetch: attachment byte size grew; `ac:name="toc"` still present if it was there.

If the wiki figure is gray/uncolored, Confluence stripped SVG `<style>`. Tell the user and attach a PNG screenshot of the HTML viewer instead of inventing inline `fill=` on every node.

## Do not

| Action | Do this instead |
|---|---|
| Scrape inner SVG + paste a few CSS variables | Run `compose-page-svg.mjs` |
| Treat Export → SVG as a full page | Compose `*.page.svg` |
| Leave dual-theme / `autoTheme` for wiki | Lock `--theme light --preset classic` |
| `content_format=markdown` on a page with TOC | Storage HTML, surgical edit |
| Publish Archify via pretty-mermaid | SVG attachment |
| Put “Archify SVG locked to light + classic” (or any export/theme boilerplate) in the wiki body | Keep lock in `compose-page-svg.mjs`; wiki intro stays technical scope |
| Claim visual match without opening the SVG | Local preview, then wiki hard-refresh |

## Example

```bash
node ~/.cursor/skills/exporting-archify-svg/scripts/compose-page-svg.mjs \
  xpon-apps/metrics-mgr/docs/archify/cpmp-kafka-sink.html
```

Then upload `cpmp-kafka-sink.page.svg` to the target Confluence page as `ac:image` / `ri:attachment`.
