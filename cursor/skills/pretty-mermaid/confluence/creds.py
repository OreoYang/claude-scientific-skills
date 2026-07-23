#!/usr/bin/env python3
"""Load Confluence API credentials from env or Cursor MCP config."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path


def load_confluence_auth(mcp_json: Path | None = None) -> str:
    """Return HTTP Basic auth header value (base64 user:token)."""
    user = os.environ.get("CONFLUENCE_USERNAME", "").strip()
    token = os.environ.get("CONFLUENCE_API_TOKEN", "").strip()
    if user and token:
        return base64.b64encode(f"{user}:{token}".encode()).decode()

    mcp_path = mcp_json or Path.home() / ".cursor" / "mcp.json"
    if not mcp_path.is_file():
        raise FileNotFoundError(
            "Confluence credentials not found. Set CONFLUENCE_USERNAME and "
            "CONFLUENCE_API_TOKEN, or configure ~/.cursor/mcp.json (atlassian env)."
        )
    data = json.loads(mcp_path.read_text(encoding="utf-8"))
    env = data["mcpServers"]["atlassian"]["env"]
    user = env["CONFLUENCE_USERNAME"]
    token = env["CONFLUENCE_API_TOKEN"]
    return base64.b64encode(f"{user}:{token}".encode()).decode()
