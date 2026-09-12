# Official mermaid.js themes

Renderer is **mermaid.js** (mermaid.live / mermaid.ink), not beautiful-mermaid.

## Themes

| Name | Use |
|------|-----|
| `default` | Light, mermaid.live default. **Use this for Confluence.** |
| `dark` | Dark background docs |
| `forest` | Green accent |
| `neutral` | Gray / low color |
| `base` | mermaid “base” theme |

```bash
node ~/.cursor/skills/pretty-mermaid/scripts/themes.mjs
node ~/.cursor/skills/pretty-mermaid/scripts/render.mjs \
  --input diagram.mmd --output diagram.svg --theme default
```

Per-diagram override: put `%%{init: {"theme": "dark"}}%%` at the top of the `.mmd`. That wins over `--theme`.

## Legacy aliases (pretty-mermaid 1.x)

Old beautiful-mermaid names still work on the CLI; they map to official themes:

| Alias | Maps to |
|-------|---------|
| `github-light`, `zinc-light`, `solarized-light`, `tokyo-night-light`, `nord-light`, `catppuccin-latte` | `default` |
| `github-dark`, `tokyo-night`, `tokyo-night-storm`, `dracula`, `nord`, `one-dark`, `zinc-dark`, `solarized-dark`, `catppuccin-mocha` | `dark` |

Do not expect tokyo-night palettes — those belonged to beautiful-mermaid.

## Custom colors

Use mermaid.js `classDef` / `style` in the diagram source, or `%%{init: {"themeVariables": {...}}}%%`. The CLI no longer takes `--bg` / `--fg` / `--line` (those were beautiful-mermaid).
