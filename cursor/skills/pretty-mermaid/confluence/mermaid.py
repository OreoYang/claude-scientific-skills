#!/usr/bin/env python3
"""Confluence Mermaid diagram helpers (pretty-mermaid skill + expand macro)."""
from __future__ import annotations

import math
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
RENDER_SCRIPT = SKILL_ROOT / "scripts" / "render.mjs"
DEFAULT_THEME = "github-light"
# Edge colors for Confluence (pale github-light theme lines are hard to see on pastel nodes).
DEFAULT_LINE_COLOR = "#343a40"
DEFAULT_ACCENT_COLOR = "#1864ab"
DEFAULT_BG = "#ffffff"
DEFAULT_FG = "#0d1117"
DEFAULT_MUTED = "#0d1117"
# Near-black on pastel bands (Confluence); avoid gray tiers that wash out on tinted SVG.
DEFAULT_TEXT = "#0d1117"
DEFAULT_TEXT_SEC = "#0d1117"
DEFAULT_TEXT_MUTED = "#0d1117"
DEFAULT_TEXT_FAINT = "#212529"
# Flowchart classDef label colors → darker for contrast on pastel node fills.
_NODE_LABEL_DARKEN = {
    "#1864ab": "#04264f",
    "#d9480f": "#8a2c00",
    "#c92a2a": "#7f1d1d",
    "#0b7285": "#05505c",
    "#495057": "#0d1117",
    "#5f3dc4": "#3b2691",
    "#1e7b34": "#14532d",
    "#2b8a3e": "#14532d",
}
_EDGE_STROKE_RE = re.compile(
    r'(<polyline\b[^>]*stroke-width=")([\d.]+)(")',
    re.IGNORECASE,
)
_BR_IN_LABEL = re.compile(r"<br\s*/?>", re.IGNORECASE)
_SEQ_RECT_BLOCK_RE = re.compile(
    r'<rect (?P<outer>[^>]*\bfill="none"[^>]*)/>\s*'
    r'<rect [^>]*/>\s*'
    r'<text[^>]*>rect \[rgba\((?P<rgba>[^)]+)\)\]</text>',
    re.IGNORECASE,
)
_SEQ_BOX_RE = re.compile(
    r"box\s+rgba\(([^)]+)\)\s+[^\n]+\n((?:\s+participant\s+\w+\s+as\s+[^\n]+\n?)+)",
    re.IGNORECASE,
)
_SEQ_PARTICIPANT_RE = re.compile(
    r'<text x="(?P<x>[^"]+)" y="50"[^>]*>(?P<label>[^<]+)</text>',
)
_SEQ_LIFELINE_RE = re.compile(
    r'<line x1="(?P<x>[^"]+)" y1="(?P<y1>[^"]+)" x2="\1" y2="(?P<y2>[^"]+)"[^/]*/>',
)
_SEQ_VIEWBOX_RE = re.compile(r'viewBox="0 0 ([^"]+)"')
# Flowchart review (Mermaid cross-subgraph / cluster-anchor layout bugs).
_MMD_NODE_DEF_RE = re.compile(
    r'\b([A-Z][A-Z0-9_]*)\s*\["([^"]*)"(?:\s*:::)?[^\]]*\]',
)
_MMD_EDGE_RE = re.compile(
    r"^\s*((?:[A-Z][A-Z0-9_]*\s*(?:&\s*)?)+)\s+"
    r"((?:--+|==+|-.+)-?>)\s*"
    r"(?:\|([^|]*)\|)?\s*"
    r"((?:[A-Z][A-Z0-9_]*\s*(?:&\s*)?)+)\s*$",
    re.MULTILINE,
)
_MMD_SUBGRAPH_OPEN_RE = re.compile(r"^\s*subgraph\s+(\w+)", re.IGNORECASE | re.MULTILINE)
_MMD_SUBGRAPH_CLOSE_RE = re.compile(r"^\s*end\s*$", re.MULTILINE)
_SVG_NODE_LABEL_RE = re.compile(
    r'<text x="(?P<x>[^"]+)" y="(?P<y>[^"]+)"[^>]*font-size="13"[^>]*>'
    r'&quot;(?P<label>(?:[^&]|&(?!quot;))*)&quot;</text>',
)
_SVG_EDGE_LABEL_RE = re.compile(
    r'<text x="(?P<x>[^"]+)" y="(?P<y>[^"]+)"[^>]*>'
    r"(?P<label>(?:⚠\s*)?[^<]+)</text>",
)
_SVG_POLYLINE_RE = re.compile(
    r'<polyline points="(?P<pts>[^"]+)"[^>]*marker-end="url\(#arrowhead\)"',
)
_SVG_GROUP_HDR_RE = re.compile(
    r'<text x="[^"]+" y="(?P<y>[^"]+)"[^>]*>&quot;(?P<label>[①②③④⑤⑥⑦⑧⑨⑩][^"]*)&quot;</text>',
)
_NODE_HIT_RADIUS_PX = 110.0
_WRONG_NODE_ERROR_PX = 85.0
_LABEL_TO_POLYLINE_PX = 50.0


@dataclass(frozen=True)
class LayoutReviewFinding:
    severity: str  # "error" | "warn"
    message: str


def _split_mmd_ids(blob: str) -> list[str]:
    return [p.strip() for p in re.split(r"\s*&\s*", blob.strip()) if p.strip()]


def _parse_flowchart_mmd(mmd_source: str) -> tuple[dict[str, str], list[tuple[str, str, str]], dict[str, str]]:
    """Return node labels, edges (src, tgt, label), node→subgraph id."""
    if "flowchart" not in mmd_source:
        return {}, [], {}

    labels: dict[str, str] = {}
    for m in _MMD_NODE_DEF_RE.finditer(mmd_source):
        labels[m.group(1)] = m.group(2).strip()

    node_subgraph: dict[str, str] = {}
    subgraph_stack: list[str] = []
    for line in mmd_source.splitlines():
        if _MMD_SUBGRAPH_OPEN_RE.match(line):
            subgraph_stack.append(_MMD_SUBGRAPH_OPEN_RE.match(line).group(1))
            continue
        if _MMD_SUBGRAPH_CLOSE_RE.match(line):
            if subgraph_stack:
                subgraph_stack.pop()
            continue
        nm = _MMD_NODE_DEF_RE.search(line)
        if nm and subgraph_stack:
            node_subgraph[nm.group(1)] = subgraph_stack[-1]

    edges: list[tuple[str, str, str]] = []
    for m in _MMD_EDGE_RE.finditer(mmd_source):
        srcs = _split_mmd_ids(m.group(1))
        tgts = _split_mmd_ids(m.group(4))
        label = (m.group(3) or "").strip()
        for src in srcs:
            for tgt in tgts:
                if src in labels and tgt in labels:
                    edges.append((src, tgt, label))
    return labels, edges, node_subgraph


def _parse_flowchart_svg_nodes(svg: str) -> dict[str, tuple[float, float]]:
    """Map node label text → center (x, y) from rendered node captions."""
    positions: dict[str, tuple[float, float]] = {}
    for m in _SVG_NODE_LABEL_RE.finditer(svg):
        label = m.group("label").strip()
        positions[label] = (float(m.group("x")), float(m.group("y")))
    return positions


def _parse_flowchart_svg_arrows(svg: str) -> list[tuple[float, float, list[tuple[float, float]]]]:
    """Arrow tip (ex, ey) and full point list for each directed edge."""
    arrows: list[tuple[float, float, list[tuple[float, float]]]] = []
    for m in _SVG_POLYLINE_RE.finditer(svg):
        pts = [
            (float(x), float(y))
            for x, y in (p.split(",") for p in m.group("pts").split())
        ]
        if len(pts) < 2:
            continue
        ex, ey = pts[-1]
        arrows.append((ex, ey, pts))
    return arrows


def _nearest_label(
    pos: tuple[float, float],
    label_positions: dict[str, tuple[float, float]],
) -> tuple[str, float] | None:
    best: tuple[str, float] | None = None
    for label, (lx, ly) in label_positions.items():
        dist = math.hypot(pos[0] - lx, pos[1] - ly)
        if best is None or dist < best[1]:
            best = (label, dist)
    return best


def _arrow_tip_for_labeled_edge(
    label: str,
    arrows: list[tuple[float, float, list[tuple[float, float]]]],
    svg: str,
    target_pos: tuple[float, float],
) -> tuple[float, float] | None:
    m = re.search(
        rf'<text x="(?P<x>[^"]+)" y="(?P<y>[^"]+)"[^>]*>{re.escape(label)}</text>',
        svg,
    )
    if not m:
        return None
    lx, ly = float(m.group("x")), float(m.group("y"))
    tx, ty = target_pos
    candidates: list[tuple[float, float, float]] = []
    for ex, ey, pts in arrows:
        if not any(
            math.hypot(px - lx, py - ly) < _LABEL_TO_POLYLINE_PX for px, py in pts
        ):
            continue
        candidates.append((ex, ey, math.hypot(ex - tx, ey - ty)))
    if not candidates:
        return None
    best = min(candidates, key=lambda c: c[2])
    return (best[0], best[1])


def review_mermaid_layout(mmd_source: str, svg: str) -> list[LayoutReviewFinding]:
    """Heuristic SVG review: arrow targets, cross-subgraph edges, TB layer order."""
    findings: list[LayoutReviewFinding] = []
    if "flowchart" not in mmd_source:
        return findings

    id_labels, edges, node_subgraph = _parse_flowchart_mmd(mmd_source)
    if not id_labels:
        return findings

    label_pos = _parse_flowchart_svg_nodes(svg)
    id_pos: dict[str, tuple[float, float]] = {}
    for nid, label in id_labels.items():
        if label in label_pos:
            id_pos[nid] = label_pos[label]

    arrows = _parse_flowchart_svg_arrows(svg)

    for src, tgt, elabel in edges:
        sg_src = node_subgraph.get(src)
        sg_tgt = node_subgraph.get(tgt)
        cross_subgraph = bool(sg_src and sg_tgt and sg_src != sg_tgt)
        if src not in id_pos or tgt not in id_pos:
            continue
        tip: tuple[float, float] | None
        if elabel:
            tip = _arrow_tip_for_labeled_edge(elabel, arrows, svg, id_pos[tgt])
        else:
            # Prefer arrow whose *start* is near src and tip near tgt (chain-safe).
            sx, sy = id_pos[src]
            tx, ty = id_pos[tgt]
            best_tip: tuple[float, float] | None = None
            best_score = float("inf")
            for ex, ey, pts in arrows:
                start = pts[0]
                score = math.hypot(start[0] - sx, start[1] - sy) + math.hypot(
                    ex - tx, ey - ty
                )
                if score < best_score:
                    best_score = score
                    best_tip = (ex, ey)
            tip = best_tip if best_score < _NODE_HIT_RADIUS_PX * 3 else None
        if tip is None:
            if elabel:
                findings.append(
                    LayoutReviewFinding(
                        "warn",
                        f"Edge {src} → {tgt} |{elabel}|: "
                        "could not match arrow in SVG; verify manually.",
                    )
                )
            continue

        # Labeled edges: only ERROR when tip is clearly on a *wrong* node.
        # Unlabeled: WARN only (matching is heuristic).
        nearest = _nearest_label(tip, label_pos)
        if nearest is None:
            continue
        hit_label, hit_dist = nearest
        expected_label = id_labels[tgt]
        tip_to_expected = math.hypot(tip[0] - id_pos[tgt][0], tip[1] - id_pos[tgt][1])
        # Wide nodes: tip may hit the left/right edge far from text center — still correct.
        same_band = abs(tip[1] - id_pos[tgt][1]) < 36
        if same_band and tip_to_expected < 200:
            continue

        if hit_label != expected_label and tip_to_expected > _NODE_HIT_RADIUS_PX:
            sev = "error" if elabel and hit_dist < _WRONG_NODE_ERROR_PX else "warn"
            findings.append(
                LayoutReviewFinding(
                    sev,
                    f"Edge {src} → {tgt}"
                    f"{f' |{elabel}|' if elabel else ''}: "
                    f"arrow tip lands on «{hit_label}» ({hit_dist:.0f}px), "
                    f"expected «{expected_label}» ({tip_to_expected:.0f}px away).",
                )
            )
        elif cross_subgraph and tip_to_expected > _NODE_HIT_RADIUS_PX:
            findings.append(
                LayoutReviewFinding(
                    "warn",
                    f"Cross-subgraph edge {src} → {tgt}"
                    f"{f' |{elabel}|' if elabel else ''}: "
                    f"tip {tip_to_expected:.0f}px from expected «{expected_label}». "
                    "Consider a bridge node outside subgraphs.",
                )
            )

    # Cluster-border artifact: tip on far left margin, not near any node.
    for ex, ey, _ in arrows:
        if ex > 80:
            continue
        nearest = _nearest_label((ex, ey), label_pos)
        if nearest and nearest[1] > _NODE_HIT_RADIUS_PX:
            findings.append(
                LayoutReviewFinding(
                    "error",
                    f"Arrow tip at ({ex:.0f},{ey:.0f}) looks like a subgraph-border anchor "
                    f"(nearest «{nearest[0]}» {nearest[1]:.0f}px away).",
                )
            )

    # TB swimlane headers should not overlap (monotonic y).
    layers = [(float(m.group("y")), m.group("label")[:40]) for m in _SVG_GROUP_HDR_RE.finditer(svg)]
    if len(layers) >= 2:
        prev_y = layers[0][0]
        for y, name in layers[1:]:
            if y < prev_y + 40:
                findings.append(
                    LayoutReviewFinding(
                        "warn",
                        f"Subgraph vertical overlap: «{name}» (y={y:.0f}) "
                        f"may overlap prior layer (y={prev_y:.0f}).",
                    )
                )
            prev_y = y

    return findings


def print_layout_review(findings: list[LayoutReviewFinding], diagram: str = "") -> None:
    if not findings:
        return
    prefix = f"{diagram}: " if diagram else ""
    for f in findings:
        tag = "ERROR" if f.severity == "error" else "WARN"
        print(f"{prefix}[mermaid-review] {tag}: {f.message}", file=sys.stderr)


def review_mermaid_layout_file(mmd_source: str, svg_path: Path) -> list[LayoutReviewFinding]:
    if not svg_path.is_file():
        return []
    return review_mermaid_layout(mmd_source, svg_path.read_text(encoding="utf-8"))


def normalize_mermaid_br(mmd_text: str) -> str:
    """Replace HTML line breaks in Mermaid labels with middot separators."""
    return _BR_IN_LABEL.sub(" · ", mmd_text)


def _deepen_svg_text(svg: str, mmd_source: str = "") -> str:
    """Raise contrast for labels on pastel sequence/flowchart backgrounds."""
    style_pairs = [
        (
            "--_text:          var(--fg);",
            f"--_text:          {DEFAULT_TEXT};",
        ),
        (
            "--_text-sec:      var(--muted, color-mix(in srgb, var(--fg) 60%, var(--bg)));",
            f"--_text-sec:      {DEFAULT_TEXT_SEC};",
        ),
        (
            "--_text-muted:    var(--muted, color-mix(in srgb, var(--fg) 40%, var(--bg)));",
            f"--_text-muted:    {DEFAULT_TEXT_MUTED};",
        ),
        (
            "--_text-faint:    color-mix(in srgb, var(--fg) 25%, var(--bg));",
            f"--_text-faint:    {DEFAULT_TEXT_FAINT};",
        ),
    ]
    for old, new in style_pairs:
        svg = svg.replace(old, new)
    # Idempotent re-publish: already-patched CSS variables.
    svg = re.sub(r"--_text-muted:\s*[^;]+;", f"--_text-muted: {DEFAULT_TEXT_MUTED};", svg)
    svg = re.sub(r"--_text-sec:\s*[^;]+;", f"--_text-sec: {DEFAULT_TEXT_SEC};", svg)
    svg = re.sub(r"--_text:\s*[^;]+;", f"--_text: {DEFAULT_TEXT};", svg)

    svg = re.sub(
        r'(<svg[^>]*style="[^"]*)--fg:[^;"]+',
        rf"\1--fg:{DEFAULT_FG}",
        svg,
        count=1,
    )
    if f"--muted:{DEFAULT_MUTED}" not in svg:
        svg = re.sub(
            r'(<svg[^>]*style="[^"]*)',
            rf'\1--muted:{DEFAULT_MUTED};',
            svg,
            count=1,
        )

    for pale, dark in _NODE_LABEL_DARKEN.items():
        svg = svg.replace(f'fill="{pale}"', f'fill="{dark}"')

    svg = svg.replace('fill="var(--_text-muted)"', f'fill="{DEFAULT_TEXT_MUTED}"')
    svg = svg.replace('fill="var(--_text-sec)"', f'fill="{DEFAULT_TEXT_SEC}"')
    svg = svg.replace('fill="var(--_text)"', f'fill="{DEFAULT_TEXT}"')
    svg = svg.replace('fill="var(--_text-faint)"', f'fill="{DEFAULT_TEXT_FAINT}"')
    if "sequenceDiagram" in mmd_source:
        svg = re.sub(
            r'(<text\b[^>]*font-size="11"[^>]*)font-weight="(?:400|500|600)"',
            r'\1font-weight="600"',
            svg,
        )
        svg = re.sub(
            r'(<text\b[^>]*)font-size="11"',
            r'\1font-size="12"',
            svg,
        )
    else:
        svg = re.sub(
            r'(<text\b[^>]*font-size="11"[^>]*)font-weight="400"',
            r'\1font-weight="500"',
            svg,
        )
        svg = re.sub(
            r'(<text\b[^>]*font-size="13"[^>]*)font-weight="500"',
            r'\1font-weight="600"',
            svg,
        )
    return svg


def enhance_mermaid_svg(svg_path: Path, mmd_source: str = "") -> None:
    """Thicken strokes; paint sequence diagram section/column backgrounds."""
    text = svg_path.read_text(encoding="utf-8")

    def _thicken(match: re.Match[str]) -> str:
        width = float(match.group(2))
        return f'{match.group(1)}{max(width * 2.0, 1.75):g}{match.group(3)}'

    text = _EDGE_STROKE_RE.sub(_thicken, text)
    if "seq-arrow" in text or "sequenceDiagram" in mmd_source:
        text = _colorize_sequence_svg(text, mmd_source)
    text = _deepen_svg_text(text, mmd_source)
    svg_path.write_text(text, encoding="utf-8")


def _stack_path_section_rects(svg: str) -> str:
    """Stack full-width path section bands when beautiful-mermaid gives them the same y."""
    pat = re.compile(
        r'<rect x="30" y="(?P<y>[\d.]+)" width="(?P<w>[\d.]+)" height="(?P<h>[\d.]+)" '
        r'rx="0" ry="0" fill="(?P<fill>rgba\([^"]+\))" stroke="none" />'
    )
    matches = list(pat.finditer(svg))
    if len(matches) < 2:
        return svg
    cursor_y: float | None = None
    rebuilt: list[str] = []
    last_end = 0
    for m in matches:
        y = float(m.group("y"))
        h = float(m.group("h"))
        if cursor_y is not None and y < cursor_y:
            y = cursor_y
        rebuilt.append(svg[last_end : m.start()])
        rebuilt.append(
            f'<rect x="30" y="{y:g}" width="{m.group("w")}" height="{h:g}" '
            f'rx="0" ry="0" fill="{m.group("fill")}" stroke="none" />'
        )
        cursor_y = y + h
        last_end = m.end()
    rebuilt.append(svg[last_end:])
    return "".join(rebuilt)


def _colorize_sequence_svg(svg: str, mmd_source: str) -> str:
    """beautiful-mermaid emits rect/box rgba as fill=none; restore intended tints."""

    def _paint_rect_block(m: re.Match[str]) -> str:
        outer = re.sub(
            r'\bfill="none"',
            f'fill="rgba({m.group("rgba")})"',
            m.group("outer"),
        )
        return f"<rect {outer}/>"

    svg = _SEQ_RECT_BLOCK_RE.sub(_paint_rect_block, svg)
    svg = re.sub(r'\bfill="none"([^>]*)\s+fill="rgba', r'fill="rgba', svg)

    vb = _SEQ_VIEWBOX_RE.search(svg)
    if not vb:
        return svg
    total_w = float(vb.group(1).split()[0])
    bands: list[str] = []

    # Expand mermaid path-section rects to full diagram width.
    def _widen_path_rect(m: re.Match[str]) -> str:
        tag = m.group(0)
        y = m.group("y")
        h = m.group("h")
        fill_m = re.search(r'fill="(rgba\([^"]+\))"', tag)
        if not fill_m:
            return tag
        fill = fill_m.group(1)
        return (
            f'<rect x="30" y="{y}" width="{total_w - 60:g}" height="{h}" '
            f'rx="0" ry="0" fill="{fill}" stroke="none" />'
        )

    svg = re.sub(
        r'<rect x="[^"]+" y="(?P<y>[^"]+)" width="[^"]+" height="(?P<h>[^"]+)"[^>]*'
        r'fill="rgba\([^"]+\)"[^>]*/>',
        _widen_path_rect,
        svg,
    )
    svg = _stack_path_section_rects(svg)

    lifelines = sorted({float(m.group("x")) for m in _SEQ_LIFELINE_RE.finditer(svg)})
    if lifelines:
        y_top = min(float(m.group("y1")) for m in _SEQ_LIFELINE_RE.finditer(svg))
        y_bot = max(float(m.group("y2")) for m in _SEQ_LIFELINE_RE.finditer(svg))
        height = y_bot - y_top
        bounds = [30.0]
        bounds.extend((lifelines[i] + lifelines[i + 1]) / 2.0 for i in range(len(lifelines) - 1))
        bounds.append(total_w - 30.0)

        label_to_x: dict[str, float] = {}
        for m in _SEQ_PARTICIPANT_RE.finditer(svg):
            label_to_x[m.group("label").strip().strip('"')] = float(m.group("x"))

        id_to_x: dict[str, float] = {}
        for m in re.finditer(r"participant\s+(\w+)\s+as\s+([^\n]+)", mmd_source, re.IGNORECASE):
            pid, alias = m.group(1), m.group(2).strip()
            for label, x in label_to_x.items():
                if alias in label or label in alias:
                    id_to_x[pid] = x
                    break

        for box_m in _SEQ_BOX_RE.finditer(mmd_source):
            rgba = box_m.group(1).strip()
            ids = re.findall(r"participant\s+(\w+)\s+as", box_m.group(2), re.IGNORECASE)
            xs = [id_to_x[i] for i in ids if i in id_to_x]
            if not xs:
                continue
            indices = sorted(lifelines.index(x) for x in xs)
            x_left = bounds[indices[0]]
            x_right = bounds[indices[-1] + 1]
            bands.append(
                f'<rect x="{x_left:g}" y="{y_top:g}" width="{x_right - x_left:g}" '
                f'height="{height:g}" fill="rgba({rgba})" stroke="none" />'
            )

        for m in _SEQ_PARTICIPANT_RE.finditer(svg):
            label = m.group("label").strip().strip('"')
            fill = None
            for box_m in _SEQ_BOX_RE.finditer(mmd_source):
                rgba = box_m.group(1).strip()
                aliases = re.findall(r"as\s+([^\n]+)", box_m.group(2), re.IGNORECASE)
                if any(a.strip() in label or label in a.strip() for a in aliases):
                    fill = f"rgba({rgba})"
                    break
            if not fill:
                continue
            marker = f'<text x="{m.group("x")}" y="50"'
            pos = svg.find(marker)
            if pos == -1:
                continue
            head_start = svg.rfind("<rect", 0, pos)
            if head_start == -1:
                continue
            head_end = svg.find("/>", head_start) + 2
            head = svg[head_start:head_end]
            new_head = re.sub(r'fill="[^"]+"', f'fill="{fill}"', head, count=1)
            svg = svg[:head_start] + new_head + svg[head_end:]

    if bands:
        insert = f'<g id="seq-background-bands">{"".join(bands)}</g>'
        svg = svg.replace("</defs>", f"</defs>{insert}", 1)
    return svg


def slugify(text: str, max_len: int = 48) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.lower()).strip("-")
    return (s[:max_len] or "diagram").strip("-")


def render_mermaid_svg(mmd_text: str, output_svg: Path, theme: str = DEFAULT_THEME) -> None:
    mmd_text = normalize_mermaid_br(mmd_text)
    if not RENDER_SCRIPT.is_file():
        raise FileNotFoundError(
            f"render.mjs not found at {RENDER_SCRIPT}; "
            "run npm install in pretty-mermaid skill root"
        )
    output_svg.parent.mkdir(parents=True, exist_ok=True)
    mmd_file = output_svg.with_suffix(".mmd")
    mmd_file.write_text(mmd_text.strip() + "\n", encoding="utf-8")
    cmd = [
        "node",
        str(RENDER_SCRIPT),
        "--input",
        str(mmd_file),
        "--output",
        str(output_svg),
        "--bg",
        DEFAULT_BG,
        "--fg",
        DEFAULT_FG,
        "--muted",
        DEFAULT_MUTED,
        "--line",
        DEFAULT_LINE_COLOR,
        "--accent",
        DEFAULT_ACCENT_COLOR,
    ]
    subprocess.run(
        cmd,
        check=True,
        capture_output=True,
        text=True,
    )
    if not output_svg.is_file():
        raise RuntimeError(f"render.mjs did not produce {output_svg}")
    enhance_mermaid_svg(output_svg, mmd_text)
    findings = review_mermaid_layout_file(mmd_text, output_svg)
    print_layout_review(findings, output_svg.name)
    errors = [f for f in findings if f.severity == "error"]
    if errors:
        raise RuntimeError(
            f"Mermaid layout review failed for {output_svg.name} "
            f"({len(errors)} error(s)); fix .md diagram or bridge nodes. "
            "See stderr for [mermaid-review] messages."
        )


def svg_dimensions(svg_path: Path) -> tuple[int | None, int | None]:
    try:
        root = ET.parse(svg_path).getroot()
    except ET.ParseError:
        return None, None
    viewbox = root.attrib.get("viewBox")
    if viewbox:
        parts = viewbox.split()
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

    parser = argparse.ArgumentParser(description="Confluence Mermaid helpers")
    sub = parser.add_subparsers(dest="cmd", required=True)
    review_p = sub.add_parser("review", help="Review flowchart arrow/layout vs .mmd")
    review_p.add_argument("mmd", type=Path)
    review_p.add_argument("svg", type=Path)
    args = parser.parse_args()
    if args.cmd == "review":
        findings = review_mermaid_layout_file(
            args.mmd.read_text(encoding="utf-8"),
            args.svg,
        )
        print_layout_review(findings, args.svg.name)
        return 1 if any(f.severity == "error" for f in findings) else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
