#!/usr/bin/env python3
"""Publish Markdown (with ```mermaid blocks) to Confluence via pretty-mermaid.

Usage:
  python3 ~/.cursor/skills/pretty-mermaid/confluence/publish.py \\
    --config path/to/page.publish.json

Credentials: CONFLUENCE_USERNAME + CONFLUENCE_API_TOKEN, or ~/.cursor/mcp.json.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

from creds import load_confluence_auth
from ascii_art import AsciiArtError, is_box_diagram, validate_ascii_art_strict
from mermaid import (
    mermaid_diagram_block,
    render_mermaid_svg,
    slugify,
)
from page import ensure_page_full_width


def _resolve(base: Path, value: str) -> Path:
    p = Path(value)
    return p if p.is_absolute() else (base / p).resolve()


def load_config(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    base = path.parent
    cfg["_base"] = base
    cfg["_md_file"] = _resolve(base, cfg["md_file"])
    cfg["_storage_file"] = _resolve(base, cfg.get("storage_file", cfg["md_file"] + ".storage.html"))
    cfg["_diagram_dir"] = _resolve(base, cfg.get("diagram_dir", "mermaid-svg"))
    if "intro_html_file" in cfg:
        cfg["_intro_html"] = _resolve(base, cfg["intro_html_file"]).read_text(encoding="utf-8")
    else:
        cfg["_intro_html"] = cfg.get("intro_html", "")
    return cfg


def code_macro(body: str, language: str = "none") -> str:
    return (
        '<ac:structured-macro ac:name="code" ac:schema-version="1">'
        f'<ac:parameter ac:name="language">{language}</ac:parameter>'
        f"<ac:plain-text-body><![CDATA[{body}]]></ac:plain-text-body>"
        "</ac:structured-macro>"
    )


def normalize_fenced_code(raw: str) -> str:
    """Trim empty lines around a fenced block; preserve trailing spaces on content lines."""
    lines = raw.split("\n")
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def format_inline_md(text: str) -> str:
    text = html.escape(text)
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


def md_table_to_html(lines: list[str]) -> str:
    rows = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(set(c) <= set("-:") for c in cells):
            continue
        tag = "th" if i == 0 else "td"
        row = "".join(f"<{tag}><p>{format_inline_md(c)}</p></{tag}>" for c in cells)
        rows.append(f"<tr>{row}</tr>")
    if not rows:
        return ""
    return (
        '<table data-layout="wide" data-table-width="960"><tbody>'
        + "".join(rows)
        + "</tbody></table>"
    )


class DiagramRegistry:
    def __init__(self, prefix: str, diagram_dir: Path) -> None:
        self._counter = 0
        self._prefix = prefix
        self._diagram_dir = diagram_dir
        self.attachments: list[Path] = []

    def next(self, section_title: str, mmd_source: str) -> str:
        self._counter += 1
        slug = slugify(section_title)
        attachment_name = f"{self._prefix}-{self._counter:02d}-{slug}.svg"
        svg_path = self._diagram_dir / attachment_name
        render_mermaid_svg(mmd_source, svg_path)
        self.attachments.append(svg_path)
        expand_title = f"Mermaid source — {section_title} (#{self._counter})"
        return mermaid_diagram_block(attachment_name, mmd_source, svg_path, expand_title)


def parse_md_sections(text: str) -> list[tuple[str, str]]:
    parts = re.split(r"\n(?=## )", text)
    sections = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("# "):
            continue
        if part.startswith("## "):
            title, _, body = part.partition("\n")
            sections.append((title[3:].strip(), body.strip()))
    return sections


def render_prose(text: str) -> str:
    chunks = []
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("|"):
            table_lines = []
            while i < len(lines) and lines[i].startswith("|"):
                table_lines.append(lines[i])
                i += 1
            chunks.append(md_table_to_html(table_lines))
            continue
        if line.strip() == "---":
            chunks.append("<hr/>")
            i += 1
            continue
        heading = re.match(r"^(#{3,6})\s+(.+)$", line.strip())
        if heading:
            level = len(heading.group(1))
            chunks.append(f"<h{level}>{format_inline_md(heading.group(2))}</h{level}>")
            i += 1
            continue
        if line.startswith("**") and line.endswith("**"):
            chunks.append(f"<p><strong>{html.escape(line.strip('*'))}</strong></p>")
            i += 1
            continue
        if line.strip():
            chunks.append(f"<p>{format_inline_md(line)}</p>")
        i += 1
    return "\n".join(chunks)


def _prose_skips_next_fence(prose: str) -> bool:
    """True when prose ends with <!-- publish:skip --> or 'repo only' maintainer note."""
    if re.search(r"<!--\s*publish:skip\s*-->\s*$", prose):
        return True
    tail = prose.rsplit("\n", 1)[-1].lower()
    return "repo only" in tail and "not published" in tail


def render_section(title: str, body: str, diagrams: DiagramRegistry) -> str:
    out = [f"<h2>{html.escape(title)}</h2>"]
    remaining = body
    while remaining:
        m = re.search(r"```(\w+)?\n", remaining)
        if not m:
            break
        before = remaining[: m.start()]
        before_stripped = before.strip()
        lang = m.group(1) or "none"
        end = remaining.find("```", m.end())
        if end < 0:
            break
        code = normalize_fenced_code(remaining[m.end() : end])
        if _prose_skips_next_fence(before):
            if before_stripped:
                out.append(render_prose(before_stripped))
            remaining = remaining[end + 3 :].strip()
            continue
        if before_stripped:
            out.append(render_prose(before_stripped))
        if lang == "mermaid":
            out.append(diagrams.next(title, code))
        else:
            if is_box_diagram(code):
                try:
                    validate_ascii_art_strict(code, label=f"{title} (``` block)")
                except AsciiArtError as e:
                    raise AsciiArtError(f"ASCII layout check failed: {e}") from e
            out.append(code_macro(code, lang))
        remaining = remaining[end + 3 :].strip()
    if remaining:
        out.append(render_prose(remaining))
    return "\n".join(out)


def build_sections_html(md_text: str, skip_sections: list[str], diagrams: DiagramRegistry) -> str:
    skip = set(skip_sections)
    sections_html = []
    for title, body in parse_md_sections(md_text):
        if title in skip or any(s in title for s in skip):
            continue
        sections_html.append(render_section(title, body, diagrams))
    return "\n".join(sections_html)


def build_storage_html(
    md_text: str,
    intro_html: str,
    skip_sections: list[str],
    diagrams: DiagramRegistry,
    *,
    include_intro: bool = True,
) -> str:
    sections = build_sections_html(md_text, skip_sections, diagrams)
    if include_intro:
        return intro_html + sections
    return sections


def find_preserve_split(published_body: str, cfg: dict) -> tuple[int, str]:
    """Return (index, matched_anchor_html) for preserve_before_* config."""
    exact = cfg.get("preserve_before_anchor")
    if exact:
        idx = published_body.find(exact)
        if idx >= 0:
            return idx, exact

    heading = cfg.get("preserve_before_heading")
    if heading:
        pattern = r"<h2[^>]*>" + re.escape(heading) + r"</h2>"
        m = re.search(pattern, published_body)
        if m:
            return m.start(), m.group(0)

    hints = []
    if exact:
        hints.append(f"preserve_before_anchor={exact[:60]!r}...")
    if heading:
        hints.append(f"preserve_before_heading={heading!r}")
    raise ValueError(
        "preserve anchor not found in published body (len="
        + str(len(published_body))
        + "): "
        + "; ".join(hints)
    )


def merge_published_prefix(published_body: str, cfg: dict, new_suffix: str) -> str:
    """Keep wiki prefix (UI-edited intro, TOC, prose) and replace from anchor onward."""
    idx, anchor = find_preserve_split(published_body, cfg)
    heading = cfg.get("preserve_before_heading")
    if heading:
        plain_h2 = f"<h2>{heading}</h2>"
        if new_suffix.startswith(plain_h2):
            new_suffix = new_suffix[len(plain_h2) :].lstrip("\n")
        new_suffix = anchor + new_suffix
    elif not new_suffix.startswith(anchor):
        new_suffix = anchor + new_suffix
    return published_body[:idx] + new_suffix


def api_get(auth: str, url: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {auth}", "Accept": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def api_put(auth: str, page_id: str, cloud: str, payload: dict) -> dict:
    url = f"{cloud}/wiki/rest/api/content/{page_id}"
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=body,
        method="PUT",
        headers={
            "Authorization": f"Basic {auth}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def list_attachments(auth: str, page_id: str, cloud: str) -> dict[str, str]:
    url = f"{cloud}/wiki/rest/api/content/{page_id}/child/attachment?limit=200"
    data = api_get(auth, url)
    return {item["title"]: item["id"] for item in data.get("results", [])}


def upload_attachment_multipart(
    auth: str, page_id: str, cloud: str, file_path: Path, attachment_id: str | None = None
) -> None:
    boundary = "----ConfluenceMermaidBoundary"
    filename = file_path.name
    file_data = file_path.read_bytes()
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: image/svg+xml\r\n\r\n",
        file_data,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    payload = b"".join(parts)
    if attachment_id:
        url = f"{cloud}/wiki/rest/api/content/{page_id}/child/attachment/{attachment_id}/data"
    else:
        url = f"{cloud}/wiki/rest/api/content/{page_id}/child/attachment"
    req = urllib.request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "X-Atlassian-Token": "no-check",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    with urllib.request.urlopen(req) as resp:
        resp.read()


def sync_attachments(auth: str, page_id: str, cloud: str, svg_files: list[Path]) -> None:
    existing = list_attachments(auth, page_id, cloud)
    for svg in svg_files:
        name = svg.name
        if name in existing:
            print(f"  update attachment: {name}")
            upload_attachment_multipart(auth, page_id, cloud, svg, existing[name])
        else:
            print(f"  new attachment: {name}")
            upload_attachment_multipart(auth, page_id, cloud, svg, None)


def publish(cfg: dict, *, dry_run: bool = False) -> None:
    md_file: Path = cfg["_md_file"]
    storage_file: Path = cfg["_storage_file"]
    diagram_dir: Path = cfg["_diagram_dir"]
    page_id = str(cfg["page_id"])
    cloud = cfg.get("cloud", "https://vecima.atlassian.net")
    page_title = cfg["title"]
    version_comment = cfg["version_comment"]
    attachment_prefix = cfg["attachment_prefix"]
    skip_sections = cfg.get("skip_sections", [])
    preserve_anchor = cfg.get("preserve_before_anchor") or cfg.get("preserve_before_heading")
    title_from_page = bool(cfg.get("title_from_page"))

    md_text = md_file.read_text(encoding="utf-8")
    diagrams = DiagramRegistry(attachment_prefix, diagram_dir)
    include_intro = not preserve_anchor
    sections_html = build_sections_html(md_text, skip_sections, diagrams)
    storage = build_storage_html(
        md_text,
        cfg["_intro_html"],
        skip_sections,
        diagrams,
        include_intro=include_intro,
    )

    auth = None
    published_body = None
    if preserve_anchor:
        try:
            auth = load_confluence_auth()
            page = api_get(
                auth,
                f"{cloud}/wiki/rest/api/content/{page_id}?expand=body.storage,version,title",
            )
            published_body = page["body"]["storage"]["value"]
            if title_from_page:
                page_title = page["title"]
            storage = merge_published_prefix(published_body, cfg, sections_html)
            print("Merged with published prefix (content before preserve heading kept from wiki)")
        except (urllib.error.URLError, ValueError, OSError) as e:
            if dry_run:
                print(f"WARNING: preserve_before_* merge skipped on dry-run ({e})", file=sys.stderr)
            else:
                raise

    storage_file.parent.mkdir(parents=True, exist_ok=True)
    storage_file.write_text(storage, encoding="utf-8")
    print(f"Wrote {storage_file} ({len(storage)} bytes)")
    print(f"Rendered {len(diagrams.attachments)} diagram(s) under {diagram_dir}")

    if dry_run:
        print("Dry run — skipping Confluence upload")
        return

    if auth is None:
        auth = load_confluence_auth()
    ensure_page_full_width(auth, page_id, cloud)
    print("Page layout: full-width")
    print("Syncing attachments...")
    sync_attachments(auth, page_id, cloud, diagrams.attachments)

    page = api_get(auth, f"{cloud}/wiki/rest/api/content/{page_id}?expand=body.storage,version,title")
    version = page["version"]["number"]
    if title_from_page:
        page_title = page["title"]
    if preserve_anchor and published_body is None:
        published_body = page["body"]["storage"]["value"]
        storage = merge_published_prefix(published_body, cfg, sections_html)
    payload = {
        "id": page_id,
        "type": "page",
        "title": page_title,
        "version": {"number": version + 1, "message": version_comment},
        "body": {"storage": {"value": storage, "representation": "storage"}},
    }
    result = api_put(auth, page_id, cloud, payload)
    new_ver = result["version"]["number"]
    print(f"Updated page {page_id} v{version} -> v{new_ver}")
    print(
        "Post-publish: open Confluence Edit once — API PUT does not guarantee editor health; "
        "do not run restore/sync-draft loops if Edit fails (create a fresh UI page instead).",
        file=sys.stderr,
    )
    if "page_url" in cfg:
        print(f"URL: {cfg['page_url']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish Markdown+Mermaid to Confluence")
    parser.add_argument("--config", type=Path, required=True, help="page.publish.json path")
    parser.add_argument("--dry-run", action="store_true", help="Render only; no API upload")
    args = parser.parse_args()
    if not args.config.is_file():
        print(f"Config not found: {args.config}", file=sys.stderr)
        return 1
    try:
        publish(load_config(args.config), dry_run=args.dry_run)
    except urllib.error.HTTPError as e:
        print(e.read().decode(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
