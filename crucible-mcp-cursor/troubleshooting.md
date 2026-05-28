# Crucible MCP — Troubleshooting

## Symptom: `--setup` says "read operation timed out"

| Check | Expected |
|-------|----------|
| Wrong password | `curl -u user:bad` → **401** in ~1 s |
| Right password, no params on `/filter` | Often **timeout** or **504** — not a local misconfig |
| Right password, `?author=<user>` | **200** in 1–3 s |

**Action:** If lightweight curl succeeds, ignore setup WARNING and restart Cursor.

## Symptom: ping works, MCP fails

- `ping crucible.corp.vecima.com` — ICMP only (~200–250 ms RTT is normal).
- Do not use `ping https://...` (invalid).
- Test HTTPS: `curl -I https://crucible.corp.vecima.com/` or authenticated filter URL above.
- Empty `http_proxy` / `HTTP_PROXY` is fine unless corporate policy requires a proxy (then configure consistently for curl and Cursor).

## Symptom: MCP tool times out on "list all reviews"

- `get_my_reviews` uses `filter?author=` and `filter?reviewer=` — usually OK.
- `search_reviews` with only `project=CR-CH` may hit slow server-side filter — add `author`/`reviewer` or query by review ID.
- Prefer `get_review`, `get_review_comments`, `get_review_patch` when review ID is known.

## Symptom: 401 / authentication failed

- Re-run `--setup` with correct Vecima password.
- Confirm `CRUCIBLE_USER` matches Crucible login (try short username vs `first.last`).
- Ensure `~/.crucible_credentials` is mode 600 and non-empty.

## Symptom: crucible MCP not listed in Cursor

- JSON syntax in `~/.cursor/mcp.json` (trailing commas break JSON).
- Absolute path to script in `args`.
- `uv` on PATH for Cursor’s environment (same shell as terminal).
- Full restart after editing `mcp.json`.

## Symptom: empty `crucible_mcp.py` (0 bytes)

Failed partial download. Remove and re-copy from Confluence attachment or colleague.

## Server-side 504 Gateway Timeout

nginx in front of Crucible timed out (~90 s). Not fixable on the client except:

- Use narrower API queries (author/reviewer/review id).
- Retry later or report to Crucible admins if persistent.

## Verify MCP server starts (terminal)

```bash
CRUCIBLE_URL=https://crucible.corp.vecima.com CRUCIBLE_USER=<user> \
  timeout 5 uv run ~/.cursor/mcp-servers/crucible_mcp.py 2>&1 | head -5
```

Without credentials file, expect error about missing creds (not import errors). Import errors → run `uv run` once to install deps.
