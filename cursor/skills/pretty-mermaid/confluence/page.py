#!/usr/bin/env python3
"""Shared Confluence page helpers (layout, properties)."""
from __future__ import annotations

import json
import urllib.request

CONFLUENCE_CLOUD = "https://vecima.atlassian.net"
FULL_WIDTH_KEYS = ("content-appearance-draft", "content-appearance-published")
FULL_WIDTH_VALUE = "full-width"


def ensure_page_full_width(
    auth: str,
    page_id: str,
    cloud: str = CONFLUENCE_CLOUD,
) -> None:
    """Set page appearance to full-width for draft and published views."""
    headers = {
        "Authorization": f"Basic {auth}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    url = f"{cloud}/wiki/api/v2/pages/{page_id}/properties"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        props = {p["key"]: p for p in json.load(resp).get("results", [])}

    for key in FULL_WIDTH_KEYS:
        if key in props:
            prop_id = props[key]["id"]
            prop_url = f"{url}/{prop_id}"
            payload = {
                "key": key,
                "value": FULL_WIDTH_VALUE,
                "version": {"number": props[key]["version"]["number"] + 1},
            }
            put_req = urllib.request.Request(
                prop_url,
                data=json.dumps(payload).encode(),
                method="PUT",
                headers=headers,
            )
            with urllib.request.urlopen(put_req) as resp:
                resp.read()
        else:
            body = json.dumps({"key": key, "value": FULL_WIDTH_VALUE}).encode()
            post_req = urllib.request.Request(url, data=body, method="POST", headers=headers)
            with urllib.request.urlopen(post_req) as resp:
                resp.read()
