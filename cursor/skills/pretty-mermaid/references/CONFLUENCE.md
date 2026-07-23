# Confluence publish (pretty-mermaid skill)

Markdown + Mermaid pages are published via the **pretty-mermaid** Cursor skill — not from the XPON repo.

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
  --config netconf-polt/scripts/confluence-onu-mgmt-hank-dev-mt.publish.json
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

## Repo layout (content only)

| File | Role |
|------|------|
| `confluence-*.md` | Page body; `##` sections; ` ```mermaid ` blocks |
| `confluence-*.intro.html` | Page header + TOC macro (storage HTML) |
| `confluence-*.publish.json` | page_id, title, attachment prefix, paths |
| `confluence-*-mermaid/` | Generated SVG attachments (gitignored optional) |
| `confluence-*.storage.html` | Generated storage draft (local review) |

## New page checklist

1. Add `my-page.md`, `my-page.intro.html`, `my-page.publish.json`.
2. Set `page_id`, `attachment_prefix`, `version_comment` in JSON.
3. Run `publish.py --config ... --dry-run`, fix layout review errors.
4. Publish without `--dry-run`.

## Layout review CLI

```bash
python3 ~/.cursor/skills/pretty-mermaid/confluence/mermaid.py review diagram.mmd diagram.svg
```

## Sharing with others

Give them the **skill directory** (or upstream clone + `npm install`). Repo only needs `.md` + `.publish.json` + `.intro.html` — no Python publish scripts in the project.
