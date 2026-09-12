# Official mermaid.js render API (pretty-mermaid 2.x)

SVG is fetched from **mermaid.ink** (official mermaid.js, same as mermaid.live). Kroki `POST /mermaid/svg` is the fallback.

## Encode (mermaid.ink)

```
GET {MERMAID_INK_URL}/svg/{base64url(mermaid_source)}
```

Optional: `?bgColor=transparent`

Python:

```python
import base64
b64 = base64.urlsafe_b64encode(mmd.encode()).decode().rstrip("=")
url = f"https://mermaid.ink/svg/{b64}"
```

Node:

```js
const b64 = Buffer.from(mmd, 'utf8').toString('base64url');
const url = `https://mermaid.ink/svg/${b64}`;
```

If the GET is too long or returns 400, retry with mermaid.live **pako** state:

```
GET https://mermaid.ink/svg/pako:{deflate(JSON.stringify({code, mermaid:{theme}}))}
```

(`zlib.compress(...)[2:-4]` in Python = raw deflate, same as mermaid.live.)

## Skill entry points

| Call | Path |
|------|------|
| Python (Confluence) | `confluence/mermaid.py` → `render_mermaid_svg(mmd, path, theme="default")` |
| CLI | `node scripts/render.mjs --input f.mmd --output f.svg --theme default` |
| Themes | `node scripts/themes.mjs` |

Environment:

| Variable | Default |
|----------|---------|
| `MERMAID_INK_URL` | `https://mermaid.ink` |
| `KROKI_URL` | `https://kroki.io/mermaid/svg` |

Post-process: set SVG `width`/`height` from `viewBox` (mermaid.ink often emits `100%`). No stroke thickening, no sequence rgba rewrite — official mermaid.js already paints those.

## Removed (1.x / beautiful-mermaid)

- npm package `beautiful-mermaid`
- `--bg` / `--fg` / `--line` / `--accent` / `--font`
- ASCII Mermaid (`--format ascii`, `renderMermaidAscii`)
- `enhance_mermaid_svg` / layout-review ERROR gate
- `normalize_mermaid_br()` rewriting `<br/>` → ` · ` (official mermaid.js supports `<br/>`)
