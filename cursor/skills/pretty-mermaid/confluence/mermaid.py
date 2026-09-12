#!/usr/bin/env python3
"""Confluence Mermaid helpers — official mermaid.js via mermaid.ink (mermaid.live)."""
from __future__ import annotations

import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_THEME = "default"
OFFICIAL_THEMES = ("default", "dark", "forest", "neutral", "base")
THEME_ALIAS = {
    "github-light": "default",
    "zinc-light": "default",
    "solarized-light": "default",
    "tokyo-night-light": "default",
    "nord-light": "default",
    "catppuccin-latte": "default",
    "cappuccin-latte": "default",
    "github-dark": "dark",
    "tokyo-night": "dark",
    "tokyo-night-storm": "dark",
    "dracula": "dark",
    "nord": "dark",
    "one-dark": "dark",
    "zinc-dark": "dark",
    "solarized-dark": "dark",
    "catppuccin-mocha": "dark",
    "cappuccin-mocha": "dark",
}
MERMAID_INK_BASE = os.environ.get("MERMAID_INK_URL", "https://mermaid.ink").rstrip("/")
KROKI_URL = os.environ.get("KROKI_URL", "https://kroki.io/mermaid/svg")
USER_AGENT = "pretty-mermaid/2.0 (official mermaid.js via mermaid.ink)"
_VIEWBOX_RE = re.compile(r'\bviewBox="([^"]+)"', re.IGNORECASE)


def resolve_theme(name: str | None) -> str:
    if not name:
        return DEFAULT_THEME
    key = name.strip().lower()
    if key in OFFICIAL_THEMES:
        return key
    return THEME_ALIAS.get(key, DEFAULT_THEME)


def inject_theme(mmd: str, theme: str) -> str:
    if re.search(r"%%\{\s*init", mmd, re.IGNORECASE):
        return mmd
    official = resolve_theme(theme)
    return f'%%{{init: {{"theme": "{official}"}}}}%%\n{mmd}'


def normalize_mermaid_br(mmd_text: str) -> str:
    """No-op: official mermaid.js interprets <br/> in labels."""
    return mmd_text


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _fix_svg_explicit_size(svg: str) -> str:
    """mermaid.ink emits width/height=100%; Confluence needs numeric size."""
    m = _VIEWBOX_RE.search(svg)
    if not m:
        return svg
    parts = m.group(1).replace(",", " ").split()
    if len(parts) != 4:
        return svg
    w, h = parts[2], parts[3]
    svg = re.sub(r'\bwidth="100%"', f'width="{w}"', svg, count=1, flags=re.IGNORECASE)
    svg = re.sub(r'\bheight="100%"', f'height="{h}"', svg, count=1, flags=re.IGNORECASE)
    return svg


def _http_get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _http_post(url: str, body: bytes, content_type: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "User-Agent": USER_AGENT,
            "Content-Type": content_type,
            "Accept": "image/svg+xml",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _as_svg(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    if "<svg" not in text.lower():
        raise RuntimeError(f"response is not SVG: {text[:240]!r}")
    return _fix_svg_explicit_size(text)


def _render_ink_base64(mmd: str, transparent: bool) -> str:
    qs = "?bgColor=transparent" if transparent else ""
    url = f"{MERMAID_INK_BASE}/svg/{_b64url(mmd.encode('utf-8'))}{qs}"
    return _as_svg(_http_get(url))


def _render_ink_pako(mmd_source: str, theme: str, transparent: bool) -> str:
    state = json.dumps(
        {"code": mmd_source, "mermaid": {"theme": resolve_theme(theme)}},
        separators=(",", ":"),
    )
    compressed = zlib.compress(state.encode("utf-8"), 9)[2:-4]
    qs = "?bgColor=transparent" if transparent else ""
    url = f"{MERMAID_INK_BASE}/svg/pako:{_b64url(compressed)}{qs}"
    return _as_svg(_http_get(url))


def _render_kroki(mmd: str) -> str:
    return _as_svg(_http_post(KROKI_URL, mmd.encode("utf-8"), "text/plain"))


def render_official_svg_text(
    mmd_text: str,
    theme: str = DEFAULT_THEME,
    transparent: bool = False,
) -> str:
    """Return official mermaid.js SVG (mermaid.ink, then Kroki)."""
    source = mmd_text.strip() + "\n"
    themed = inject_theme(source, theme)
    errors: list[str] = []
    for label, fn in (
        ("mermaid.ink base64", lambda: _render_ink_base64(themed, transparent)),
        ("mermaid.ink pako", lambda: _render_ink_pako(source, theme, transparent)),
        ("kroki", lambda: _render_kroki(themed)),
    ):
        try:
            return fn()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, OSError) as exc:
            errors.append(f"{label}: {exc}")
    raise RuntimeError("Official Mermaid render failed:\n  - " + "\n  - ".join(errors))


def render_mermaid_svg(
    mmd_text: str,
    output_svg: Path,
    theme: str = DEFAULT_THEME,
    transparent: bool = False,
) -> None:
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    mmd_file = output_svg.with_suffix(".mmd")
    source = mmd_text.strip() + "\n"
    mmd_file.write_text(source, encoding="utf-8")
    svg = render_official_svg_text(source, theme=theme, transparent=transparent)
    output_svg.write_text(svg, encoding="utf-8")


def slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s[:max_len] or "diagram").strip("-")


def svg_dimensions(svg_path: Path) -> tuple[int | None, int | None]:
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError:
        return None, None
    viewbox = root.attrib.get("viewBox")
    if viewbox:
        parts = viewbox.replace(",", " ").split()
        if len(parts) == 4:
            return int(float(parts[2])), int(float(parts[3]))
    w = root.attrib.get("width")
    h = root.attrib.get("height")
    if w and h:
        return int(float(re.sub(r"[^0-9.]", "", w))), int(float(re.sub(r"[^0-9.]", "", h)))
    return None, None


def attachment_image_macro(filename: str, svg_path: Path | None = None) -> str:
    w, h = (None, None)
    if svg_path and svg_path.is_file():
        w, h = svg_dimensions(svg_path)
    attrs = ['ac:align="center"', 'ac:layout="center"']
    if w:
        attrs.append(f'ac:original-width="{w}"')
    if h:
        attrs.append(f'ac:original-height="{h}"')
    if w and w > 900:
        attrs.append('ac:width="900"')
    attr_s = " ".join(attrs)
    return (
        f"<ac:image {attr_s}>"
        f'<ri:attachment ri:filename="{filename}" ri:version-at-save="1" />'
        "</ac:image>"
    )


def expand_mermaid_source_macro(title: str, mmd_source: str) -> str:
    """Image on page; Mermaid source folded in expand below (Confluence workflow)."""
    safe_title = title.replace("]]", "]]")
    return (
        '<ac:structured-macro ac:name="expand" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">{safe_title}</ac:parameter>'
        "<ac:rich-text-body>"
        '<ac:structured-macro ac:name="code" ac:schema-version="1">'
        '<ac:parameter ac:name="language">mermaid</ac:parameter>'
        f"<ac:plain-text-body><![CDATA[{mmd_source.strip()}]]></ac:plain-text-body>"
        "</ac:structured-macro>"
        "</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def mermaid_diagram_block(
    attachment_name: str,
    mmd_source: str,
    svg_path: Path,
    expand_title: str = "Mermaid source (edit .md then re-publish)",
) -> str:
    """Rendered SVG attachment + expand with Mermaid syntax underneath."""
    return (
        attachment_image_macro(attachment_name, svg_path)
        + expand_mermaid_source_macro(expand_title, mmd_source)
    )


def _main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Official mermaid.js helpers")
    sub = parser.add_subparsers(dest="cmd", required=True)
    render_p = sub.add_parser("render", help="Render .mmd → SVG via mermaid.ink")
    render_p.add_argument("mmd", type=Path)
    render_p.add_argument("svg", type=Path)
    render_p.add_argument("--theme", default=DEFAULT_THEME)
    render_p.add_argument("--transparent", action="store_true")
    review_p = sub.add_parser("review", help="No-op (official mermaid.js SVG)")
    review_p.add_argument("mmd", type=Path)
    review_p.add_argument("svg", type=Path)
    args = parser.parse_args()
    if args.cmd == "render":
        render_mermaid_svg(
            args.mmd.read_text(encoding="utf-8"),
            args.svg,
            theme=args.theme,
            transparent=args.transparent,
        )
        print(f"SVG diagram saved to {args.svg}")
        return 0
    if args.cmd == "review":
        print(
            f"{args.svg.name}: [mermaid-review] skipped — official mermaid.js SVG "
            "(foreignObject labels; not the old beautiful-mermaid layout checker).",
            file=sys.stderr,
        )
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
