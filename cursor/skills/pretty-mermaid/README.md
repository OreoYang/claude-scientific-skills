<div align="center">

# Pretty-Mermaid Skills

Render Mermaid diagrams as **official mermaid.js** SVG (same as [mermaid.live](https://mermaid.live))

No Chrome, no Puppeteer, no beautiful-mermaid.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**English** ｜ [中文](README_CN.md)

</div>

## Introduction

A Mermaid rendering skill for AI. SVG is produced by **official mermaid.js** via [mermaid.ink](https://mermaid.ink) (Kroki fallback). Confluence publish attaches that SVG plus an expand with the source.

## Features

- **Official look** — matches mermaid.live (`classDef`, `<br/>` labels, rounded nodes)
- **Themes** — `default`, `dark`, `forest`, `neutral`, `base`
- **Diagram types** — Flowchart, Sequence, State, Class, ER, and other mermaid.js types
- **Batch** — parallel HTTP renders
- **Confluence** — `confluence/publish.py` (image + expand)

## Quick Start

```bash
# List official themes
node scripts/themes.mjs

# Render one diagram
node scripts/render.mjs --input diagram.mmd --output output.svg --theme default

# Or Python (used by Confluence publish)
python3 confluence/mermaid.py render diagram.mmd output.svg --theme default

# Batch
node scripts/batch.mjs --input-dir ./diagrams --output-dir ./output --theme default
```

Needs network access to mermaid.ink. Override: `MERMAID_INK_URL`.

## Confluence

```bash
python3 ~/.cursor/skills/pretty-mermaid/confluence/publish.py \
  --config path/to/page.publish.json
```

See [references/CONFLUENCE.md](references/CONFLUENCE.md).

## Documentation

See [SKILL.md](SKILL.md).

## Requirements

- Node.js 18+ (for `fetch` / `base64url` in the CLI) **or** Python 3.10+ for `mermaid.py` / `publish.py`
- HTTPS to mermaid.ink (no npm packages required)

## License

MIT License
