#!/usr/bin/env python3
"""Validate and build fixed-width ASCII box diagrams for Confluence code macros.

Box-drawing diagrams must use a constant inner width so vertical borders align in
monospace (and in Confluence code blocks). Use build_row4() for multi-column rows.

CLI:
  python3 ascii_art.py validate path/to/block.txt
  python3 ascii_art.py validate --stdin   # read diagram from stdin
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path
from typing import List, Sequence

BOX_CHARS = set("┌┐└┘│─┬┴├┤┼")
BOX_LINE_RE = re.compile(r"^[│├└].*[│┐┘┤]$")
FULL_BOX_RE = re.compile(r"^[┌].*[┐]$")


class AsciiArtError(Exception):
    pass


def is_box_drawing_line(line: str) -> bool:
    return any(c in BOX_CHARS for c in line)


def is_box_diagram(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return False
    box_lines = sum(1 for ln in lines if is_box_drawing_line(ln))
    return box_lines >= 2


def _boxed_inner_width(line: str) -> int | None:
    if line.startswith("│") and line.endswith("│"):
        return len(line) - 2
    if line.startswith("┌") and line.endswith("┐"):
        return len(line) - 2
    return None


def validate_ascii_art(text: str, *, label: str = "diagram") -> List[str]:
    """Return human-readable warnings/errors. Empty list means OK."""
    lines = text.splitlines()
    errors: List[str] = []
    warnings: List[str] = []

    non_empty = [ln for ln in lines if ln.strip()]
    if not non_empty:
        return ["empty diagram"]

    widths = [len(ln) for ln in non_empty]
    inner_widths: List[int] = []
    for ln in non_empty:
        w = _boxed_inner_width(ln)
        if w is not None:
            inner_widths.append(w)

    if inner_widths:
        ref = inner_widths[0]
        for i, ln in enumerate(non_empty):
            w = _boxed_inner_width(ln)
            if w is not None and w != ref:
                errors.append(
                    f"{label}: line {i + 1}: boxed inner width {w} != {ref}: {ln[:60]!r}"
                )
        full_width = ref + 2
        for i, ln in enumerate(non_empty):
            if _boxed_inner_width(ln) is not None:
                continue
            if is_box_drawing_line(ln):
                # Branch rows (└──┬──) are inner-width without side │ borders.
                if len(ln) == full_width - 2:
                    continue
                if len(ln) != full_width:
                    errors.append(
                        f"{label}: line {i + 1}: expected width {full_width} or "
                        f"{full_width - 2} for box-drawing row, got {len(ln)}: {ln[:60]!r}"
                    )
            elif len(non_empty) > 1:
                target = full_width - 2
                if len(ln) != target and len(ln) != full_width:
                    warnings.append(
                        f"{label}: line {i + 1}: width {len(ln)} != inner {target} "
                        f"(or full {full_width}): {ln[:50]!r}"
                    )
    else:
        ref = max(widths)
        for i, ln in enumerate(non_empty):
            if len(ln) != ref:
                warnings.append(
                    f"{label}: line {i + 1}: width {len(ln)} != max {ref} (no box borders detected)"
                )

    for i, ln in enumerate(non_empty):
        if "  " in ln and "\t" in ln:
            warnings.append(f"{label}: line {i + 1}: mixed tabs and spaces")

    return errors + warnings


def validate_ascii_art_strict(text: str, *, label: str = "diagram") -> None:
    issues = validate_ascii_art(text, label=label)
    errors = [x for x in issues if "expected width" in x or "inner width" in x or x == "empty diagram"]
    if errors:
        raise AsciiArtError("\n".join(errors))
    if issues:
        raise AsciiArtError("\n".join(issues))


def build_row4(
    cols: Sequence[str],
    *,
    col_width: int = 24,
    num_cols: int = 4,
) -> str:
    cells: List[str] = []
    for i in range(num_cols):
        raw = cols[i] if i < len(cols) else ""
        if len(raw) > col_width:
            raw = raw[:col_width]
        cells.append(raw.ljust(col_width))
    line = "".join(cells)
    expected = col_width * num_cols
    if len(line) != expected:
        raise AsciiArtError(f"row4 width {len(line)} != {expected}")
    return line


def center_text(text: str, width: int) -> str:
    if len(text) > width:
        text = text[:width]
    pad = width - len(text)
    left = pad // 2
    return " " * left + text + " " * (pad - left)


def box_top(inner_width: int) -> str:
    return "┌" + "─" * inner_width + "┐"


def box_bottom(inner_width: int) -> str:
    return "└" + "─" * inner_width + "┘"


def box_line(inner: str) -> str:
    if any(c in "┌┐└┘" for c in inner):
        raise AsciiArtError("box_line inner content must not include outer corners")
    return "│" + inner + "│"


def grid_border_row(
    col_width: int,
    num_cols: int,
    *,
    left_cap: str,
    mid_join: str,
    right_cap: str,
) -> str:
    """Horizontal border with joins at column boundaries (every col_width chars)."""
    parts: List[str] = []
    for i in range(num_cols):
        if i == 0:
            parts.append(left_cap + "─" * (col_width - 2) + mid_join)
        elif i < num_cols - 1:
            parts.append("─" * (col_width - 1) + mid_join)
        else:
            parts.append("─" * (col_width - 1) + right_cap)
        if len(parts[-1]) != col_width:
            raise AsciiArtError(f"grid segment {i} width {len(parts[-1])} != {col_width}")
    return "".join(parts)


def bordered_row(cells: Sequence[str], col_width: int, num_cols: int = 4) -> str:
    """Row with │ at each column boundary: │cell0│cell1│… (num_cols × col_width)."""
    row = ""
    for i in range(num_cols):
        text = cells[i] if i < len(cells) else ""
        row += "│" + text[: col_width - 1].ljust(col_width - 1)
    return row


def grid_vline_row(col_width: int = 24, num_cols: int = 4) -> str:
    """Vertical │ on column boundaries (aligned with grid ┬/┴/┼)."""
    return bordered_row([""] * num_cols, col_width, num_cols)


def render_ascii_svg(ascii_text: str, svg_path: Path, *, font_size: int = 13) -> None:
    """Render diagram as SVG with explicit monospace metrics (Confluence-safe display)."""
    lines = ascii_text.splitlines()
    if not lines:
        raise AsciiArtError("empty diagram")
    char_w = 7.2
    line_h = font_size + 3
    cols = max(len(ln) for ln in lines)
    width = int(cols * char_w + 20)
    height = int(len(lines) * line_h + 20)
    text_nodes = []
    for i, line in enumerate(lines):
        y = 14 + i * line_h
        text_nodes.append(
            f'<text x="10" y="{y}">{html.escape(line)}</text>'
        )
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">\n'
        f'<rect width="100%" height="100%" fill="#f4f5f7"/>\n'
        f'<style>text {{ font-family: "DejaVu Sans Mono", "Consolas", "Courier New", '
        f'monospace; font-size: {font_size}px; fill: #172b4d; white-space: pre; }}</style>\n'
        + "\n".join(text_nodes)
        + "\n</svg>\n"
    )
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg, encoding="utf-8")


def expand_ascii_source_macro(title: str, source: str) -> str:
    escaped = html.escape(source)
    return (
        '<ac:structured-macro ac:name="expand" ac:schema-version="1">'
        f'<ac:parameter ac:name="title">{html.escape(title)}</ac:parameter>'
        "<ac:rich-text-body>"
        '<ac:structured-macro ac:name="code" ac:schema-version="1">'
        '<ac:parameter ac:name="language">text</ac:parameter>'
        '<ac:parameter ac:name="breakoutMode">wide</ac:parameter>'
        '<ac:parameter ac:name="breakoutWidth">900</ac:parameter>'
        f"<ac:plain-text-body><![CDATA[{source}]]></ac:plain-text-body>"
        "</ac:structured-macro>"
        "</ac:rich-text-body>"
        "</ac:structured-macro>"
    )


def ascii_diagram_block(
    attachment_name: str,
    ascii_source: str,
    svg_path: Path,
    expand_title: str,
) -> str:
    from mermaid import attachment_image_macro

    return (
        attachment_image_macro(attachment_name, svg_path)
        + expand_ascii_source_macro(expand_title, ascii_source)
    )


def nested_box_in_cell(
    lines: Sequence[str],
    *,
    col_width: int = 24,
    inner_box_width: int = 20,
) -> List[str]:
    """Center a nested box (without outer │) inside one column width."""
    out: List[str] = []
    pad = (col_width - inner_box_width) // 2
    for ln in lines:
        if len(ln) > inner_box_width:
            ln = ln[:inner_box_width]
        centered = " " * pad + ln.ljust(inner_box_width) + " " * (col_width - pad - inner_box_width)
        if len(centered) != col_width:
            raise AsciiArtError(f"nested cell width {len(centered)} != {col_width}")
        out.append(centered)
    return out


def build_abcd_top_level_ascii() -> str:
    """Example 4×24 multi-column box grid (sample layout for complex architecture pages)."""
    col_w = 24
    inner = col_w * 4
    ib = 20

    def row4(*cols: str) -> str:
        return build_row4(cols, col_width=col_w)

    def center(line: str) -> str:
        return center_text(line, inner)

    b_nested_top = nested_box_in_cell(["├" + "─" * (ib - 2) + "┤"], col_width=col_w, inner_box_width=ib)[0]
    b_nested = nested_box_in_cell(
        [
            "│ *_cfg_db TAILQ    │",
            "│ wr: rx_worker     │",
            "│ rd: callers       │",
            "│ voip_profile_cfg  │",
            "│ wr: sysrepo       │",
            "└" + "─" * (ib - 2) + "┘",
        ],
        col_width=col_w,
        inner_box_width=ib,
    )

    lines = [
        grid_border_row(col_w, 4, left_cap="┌", mid_join="┬", right_cap="┐"),
        bordered_row(["sysrepo_change", "pon_worker", "metrics_ipc", "DbgCli"], col_w),
        grid_border_row(col_w, 4, left_cap="└", mid_join="┴", right_cap="┘"),
        grid_vline_row(col_w),
        bordered_row(["v", "v", "v", "v"], col_w),
        center("bcmonu_mgmt_* (onu_mgmt.c facade)"),
        center("notify: SLIST cb[] + g_* singleton cbs -> scheme F (sec 3)"),
        center("validate + route"),
        bordered_row(["", "", "", ""], col_w),
        bordered_row([" actor_post / call", "", "", ""], col_w),
        bordered_row(["", "", "", ""], col_w),
        grid_border_row(col_w, 4, left_cap="├", mid_join="┼", right_cap="┤"),
        bordered_row(["v", "v", "v", "v"], col_w),
        row4("(A) per-ONU actor", "(B) OLT registry", "(C) outer PM/oper", "(D) onu_plug_unplug"),
        row4("────────────", "domain", "queues", "_teardown"),
        row4(
            "exec: rx_worker[k]",
            "cross-thread global",
            "exec: rx_worker[k]",
            "exec: rx_worker[k]",
        ),
        row4(
            "hash(pon,onu)",
            "TAILQ (not one",
            "(P2: actor_post)",
            "(actor barrier)",
        ),
        bordered_row(["", "worker only)", "", ""], col_w),
        row4(
            "scheme: actor",
            "scheme B1/B2",
            "scheme: actor_post",
            "scheme: actor_post",
        ),
        row4(
            "no new lock",
            "omci_olt_registry_",
            "no new lock",
            "no new worker",
        ),
        row4(
            "FSM/TX/RX/MIB",
            "rwlock",
            "enqueue+kick",
            "+ deinit drain",
        ),
        row4(
            "cfg_set/clear",
            b_nested_top,
            "onu_pm_req_queue",
            "omci_transport_onu_deini",
        ),
        row4(
            "(actor_post)",
            b_nested[0],
            "onu_oper_req_queue",
            "*_cfg_db_flush_for_onu",
        ),
        row4("reads", b_nested[1], "pm_me_req_queue", "bcmonu_mgmt_deinit"),
        row4("(actor_call)", b_nested[2], "oper_me_req_queue", "rx_worker pool stop"),
        row4("", b_nested[3], "(inner ME on worker)", ""),
        row4("", b_nested[4], "", ""),
        row4("", b_nested[5], "", ""),
        row4("", "profile/shaper/", "", ""),
        row4("", "sip_agent", "", ""),
    ]

    for ln in lines:
        if ln.startswith("┌") and ln.endswith("┐"):
            if len(ln) != inner:
                raise AsciiArtError(f"top border width {len(ln)} != {inner}: {ln!r}")
        else:
            if len(ln) != inner:
                raise AsciiArtError(f"row width {len(ln)} != {inner}: {ln!r}")

    body = "\n".join(lines)
    validate_ascii_art_strict(body, label="example-top-level")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="ASCII box diagram tools")
    parser.add_argument(
        "command",
        choices=["validate", "gen-abcd-top", "gen-abcd-top-svg"],
        help="gen-abcd-top* = example grid CLI (legacy names; output is generic box art)",
    )
    parser.add_argument("path", nargs="?", type=str, help="file for validate")
    parser.add_argument("--stdin", action="store_true")
    args = parser.parse_args()

    if args.command == "gen-abcd-top":
        print(build_abcd_top_level_ascii())
        return 0

    if args.command == "gen-abcd-top-svg":
        art = build_abcd_top_level_ascii()
        out = Path("box-diagram.svg")
        if args.path:
            out = Path(args.path)
        render_ascii_svg(art, out)
        print(f"Wrote {out}")
        return 0

    if args.stdin:
        text = sys.stdin.read()
    elif args.path:
        text = Path(args.path).read_text(encoding="utf-8")
    else:
        parser.error("validate requires path or --stdin")
        return 2

    # Do not str.strip() the whole diagram — trailing spaces on padded rows are significant.
    text = text.rstrip("\n")
    issues = validate_ascii_art(text)
    if issues:
        for msg in issues:
            print(msg, file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
