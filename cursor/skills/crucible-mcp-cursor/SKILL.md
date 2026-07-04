---
name: crucible-mcp-cursor
description: >-
  Installs and troubleshoots the Vecima Crucible MCP server in Cursor IDE
  (crucible_mcp.py, mcp.json, VPN, credentials). Use when setting up Crucible
  code review in Cursor, configuring crucible MCP, CR-CH reviews, or when
  connection test times out during --setup.
version: 1.0.0
---

# Crucible MCP in Cursor (Vecima)

Custom FastMCP server for **Atlassian Crucible** (`https://crucible.corp.vecima.com`). Not an official Atlassian product. Complements **Jira/Confluence MCP** (`mcp-atlassian` / `uvx mcp-atlassian`) — Jira MCP cannot query Crucible reviews.

**Berwick project key:** `CR-CH` (review IDs like `CR-CH-21075`). **Jira keys** like `CH-77165` are linked via `get_reviews_for_issue`.

## Prerequisites

| Item | Requirement |
|------|-------------|
| Network | Company VPN; host resolves to internal IP (e.g. `192.168.50.x`) |
| Tools | `uv` on PATH (`~/.local/bin/uv`); system **Python 3.10+** (3.12 is fine — **do not require 3.13**) |
| Account | Vecima username + Crucible password (no PAT; LDAP/password auth) |
| Cursor | `~/.cursor/mcp.json` editable |

## 1. Obtain `crucible_mcp.py`

Script size ~17 KB. Sources (any one):

1. **Confluence** (may need browser download): [Setup Crucible MCP in Cursor](https://vecima.atlassian.net/wiki/spaces/~tobyt/pages/177308164) — attachment `crucible_mcp.py` (`att177309819`). API download from personal spaces often returns 401/404; use browser or ask Toby/colleague.
2. Copy from a colleague: `~/.cursor/mcp-servers/crucible_mcp.py`
3. Ask Cursor to regenerate from the Confluence page tool list (see § MCP tools)

Save to:

```text
~/.cursor/mcp-servers/crucible_mcp.py
```

Verify: `wc -c ~/.cursor/mcp-servers/crucible_mcp.py` should be **~17099**, not 0.

## 2. Configure `~/.cursor/mcp.json`

Add a **`crucible`** server; keep existing servers (e.g. `atlassian`). Use **`uv run`** without `--python 3.13`:

```json
"crucible": {
  "command": "uv",
  "args": ["run", "/home/<USER>/.cursor/mcp-servers/crucible_mcp.py"],
  "env": {
    "CRUCIBLE_URL": "https://crucible.corp.vecima.com",
    "CRUCIBLE_USER": "<vecima-username>"
  }
}
```

Replace `<USER>` with the Linux home directory name. `CRUCIBLE_USER` is typically short id (e.g. `oreo.yang`), not always email.

**Do not** put the password in `mcp.json`.

## 3. One-time credentials (`--setup`)

On VPN, run interactively (password hidden):

```bash
CRUCIBLE_URL=https://crucible.corp.vecima.com CRUCIBLE_USER=<vecima-username> \
  uv run ~/.cursor/mcp-servers/crucible_mcp.py --setup
```

Writes `~/.crucible_credentials` (mode **600**, base64 `user:password`). Wrong password exits with **401** quickly.

### `--setup` WARNING is often OK

The built-in health check calls **`/rest-service/reviews-v1/filter` with no query params**. That endpoint is **slow** on Vecima Crucible (read timeout or nginx **504**). Credentials are still saved.

**Lightweight auth check** (should return HTTP 200 in 1–3 s):

```bash
curl -sS -u '<user>:<password>' -o /dev/null -w 'HTTP:%{http_code} time:%{time_total}s\n' \
  'https://crucible.corp.vecima.com/rest-service/reviews-v1/filter?author=<user>'
```

Wrong password: **401** in ~1 s. `ping crucible.corp.vecima.com` only proves ICMP, not HTTPS.

## 4. Activate

1. **Restart Cursor** (or reload MCP servers in settings).
2. Confirm **crucible** appears enabled under MCP.
3. Test in chat (examples below).

First `uv run` may download `fastmcp` and `httpx` (PEP 723 inline deps in the script).

## MCP tools (what to ask Cursor)

| User prompt (example) | Tool |
|-----------------------|------|
| Show my open code reviews | `get_my_reviews` |
| Get comments on CR-CH-21075 | `get_review_comments` |
| Which reviews are linked to CH-77165? | `get_reviews_for_issue` |
| Show the diff for CR-CH-21075 | `get_review_patch` |
| Details for CR-CH-21075 | `get_review` |
| Search reviews in CR-CH | `search_reviews` (prefer `author`/`reviewer` filters) |
| Approve / close review | `get_review_transitions` then `transition_review` |
| Create review for CH-77165 | `create_review`, `add_reviewer` |

**Fast paths:** per-review APIs (`reviews-v1/<id>/details`, `/comments`, `/patch`) usually respond in 1–3 s. **Slow paths:** unfiltered `reviews-v1/filter` or heavy `project=` searches may timeout.

## Coexistence with Atlassian MCP

```json
"mcpServers": {
  "crucible": { ... },
  "atlassian": {
    "command": "uvx",
    "args": ["mcp-atlassian"],
    "env": {
      "JIRA_URL": "https://vecima.atlassian.net",
      "CONFLUENCE_URL": "https://vecima.atlassian.net/wiki",
      ...
    }
  }
}
```

Use **Jira MCP** for issues; **Crucible MCP** for code reviews and patches.

## Agent checklist (installing for a user)

```
- [ ] VPN reachable (optional: curl filter?author=<user> with creds)
- [ ] crucible_mcp.py present and ~17 KB
- [ ] mcp.json has crucible block with correct home path
- [ ] --setup completed; ~/.crucible_credentials mode 600
- [ ] User restarted Cursor
- [ ] Smoke test: get_review_comments or get_review on a known CR-CH id
```

## Troubleshooting

See [troubleshooting.md](troubleshooting.md) for ping vs HTTPS, proxy, 504/timeouts, and MCP log hints.

## References

- Confluence: [Setup Crucible MCP in Cursor](https://vecima.atlassian.net/wiki/spaces/~tobyt/pages/177308164)
- Crucible UI: `https://crucible.corp.vecima.com/cru/<review-id>`
