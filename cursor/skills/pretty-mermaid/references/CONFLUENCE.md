# Confluence publish (pretty-mermaid skill)

Markdown + Mermaid pages are published via this skill’s `confluence/publish.py`. Page **content** (`.md`, `*.publish.json`) lives in your project repo; **publish tooling** lives here.

## Install (once per machine)

```bash
git clone https://github.com/imxv/Pretty-mermaid-skills.git ~/.cursor/skills/pretty-mermaid
cd ~/.cursor/skills/pretty-mermaid && npm install
```

Or copy an existing `~/.cursor/skills/pretty-mermaid/` tree from a teammate.

## Credentials

One of:

- `CONFLUENCE_USERNAME` + `CONFLUENCE_API_TOKEN` environment variables
- `~/.cursor/mcp.json` → `mcpServers.atlassian.env` (Cursor Atlassian MCP)

## Publish a wiki page

Each Confluence page in the repo has a `*.publish.json` next to its `.md`:

```bash
python3 ~/.cursor/skills/pretty-mermaid/confluence/publish.py \
  --config path/to/my-page.publish.json
```

`--dry-run` renders SVG + storage HTML locally without uploading.

## Skill layout

| Path | Role |
|------|------|
| `scripts/render.mjs` | beautiful-mermaid SVG renderer |
| `confluence/mermaid.py` | Confluence SVG enhance + layout review |
| `confluence/page.py` | full-width page property |
| `confluence/creds.py` | auth from env / MCP |
| `confluence/publish.py` | MD → storage HTML → Confluence API |
| `confluence/ascii_art.py` | Fixed-width ASCII box validate + SVG export helpers |

## Repo layout (content only)

| File | Role |
|------|------|
| `confluence-*.md` | Page body; `##` sections; ` ```mermaid ` blocks |
| `confluence-*.intro.html` | Page header + TOC macro (storage HTML) |
| `confluence-*.publish.json` | page_id, title, attachment prefix, paths |
| `confluence-*-mermaid/` | Generated SVG attachments (gitignored optional) |
| `confluence-*.storage.html` | Generated storage draft (local review) |
| `confluence-*-top-level.ascii` | Optional fixed-width ASCII source (validated on publish) |

**Page structure (content authoring):** follow `references/PAGE_TEMPLATE.md` — concise Parts, table-first, limited figures. Reference style: [QoS technical guide (BAL US/DS)](https://vecima.atlassian.net/wiki/spaces/~fjyang/pages/234751290).

## ASCII box diagrams (optional intro sections)

Multi-column box art must use a **constant inner width** (every row same character count; `│…│` rows = inner+2). Hand-edited spacing drifts in Confluence code macros.

```bash
# Validate before publish (also runs automatically in publish.py for ``` blocks with box chars)
python3 ~/.cursor/skills/pretty-mermaid/confluence/ascii_art.py validate path/to/diagram.ascii

# Example: export a built-in grid to ASCII or monospace SVG (see ascii_art.py CLI)
python3 ~/.cursor/skills/pretty-mermaid/confluence/ascii_art.py gen-abcd-top > path/to/diagram.ascii
python3 ~/.cursor/skills/pretty-mermaid/confluence/ascii_art.py gen-abcd-top-svg path/to/diagram.svg
```

Use `build_row4()` and the grid builders in `ascii_art.py` for new layouts; do not paste free-form ASCII into Confluence.

**Confluence display:** prefer **monospace SVG** as the visible figure; keep ASCII in an expand macro for editing. Code macros alone are unreliable for Unicode box-drawing (`┌│┴`) because browser/Confluence themes may not use strict equal-width glyphs.

## New page checklist

1. **Create empty page in Confluence UI** (not API placeholder + later PUT — draft stays on `placeholder` and Edit breaks).
2. Add `my-page.md`, `my-page.intro.html`, `my-page.publish.json`.
3. Set `page_id`, `attachment_prefix`, `version_comment` in JSON.
4. Run `publish.py --config ... --dry-run`, fix layout review errors.
5. Publish without `--dry-run`.
6. **Open Edit once** after publish; if editor fails, create a **new** UI page — do not loop restore/sync-draft.

### `*.publish.json` options

| Key | Purpose |
|-----|---------|
| `skip_sections` | `##` section titles (or substrings) omitted from generated HTML |
| `preserve_before_anchor` | Exact storage substring at split point (fragile if UI adds `local-id`) |
| `preserve_before_heading` | `<h2>` inner text (e.g. `2. Architecture overview`) — preferred when Confluence UI adds `local-id` on headings |
| `title_from_page` | `true` — do not overwrite wiki title from JSON `title` on PUT |
| `intro_html_file` | TOC + intro; omitted from generated body when `preserve_before_heading` or `preserve_before_anchor` is set (prefix already contains intro) |

**Mixed UI + scripted pages:** maintain intro / prose / tables in the Confluence UI; set `skip_sections` + `preserve_before_heading` so `publish.py` only replaces diagram sections from that heading onward.

### Safe publish (do not)

| Avoid | Why |
|-------|-----|
| Create page with placeholder body then PUT | Draft ≠ published |
| Multiple PUTs + restore / sync-draft loops | Synchrony unreconciled; Edit crashes |
| Repo fragment splice + second PUT | Drift; false “draft==pub” health |
| MCP / API full storage replace on macro-heavy pages | Drops TOC; breaks editor ADF |
| `draft/diff 200` as success signal | REST metric ≠ editor health |

Markdown maintainer blocks not for Confluence: `<!-- publish:skip -->` before a fenced block, or prose line containing `repo only` + `not published`.

### Example `my-page.publish.json`

```json
{
  "page_id": "123456789",
  "cloud": "https://your-site.atlassian.net",
  "title": "Architecture diagrams",
  "title_from_page": true,
  "version_comment": "Refresh Mermaid figures",
  "attachment_prefix": "arch",
  "md_file": "confluence-architecture.md",
  "storage_file": "confluence-architecture.storage.html",
  "diagram_dir": "confluence-architecture-mermaid",
  "intro_html_file": "confluence-architecture.intro.html",
  "skip_sections": ["Maintainer notes", "1. Intro (UI only)"],
  "preserve_before_heading": "2. Overview diagram",
  "page_url": "https://your-site.atlassian.net/wiki/spaces/TEAM/pages/123456789"
}
```

Use `preserve_before_heading` when the wiki prefix (TOC, intro prose, tables) was edited in the UI and should not be overwritten on re-publish.

## Layout review CLI

```bash
python3 ~/.cursor/skills/pretty-mermaid/confluence/mermaid.py review diagram.mmd diagram.svg
```

## Sharing with others

Give them the **skill directory** (or upstream clone + `npm install`). Repo only needs `.md` + `.publish.json` + `.intro.html` — no Python publish scripts in the project.
