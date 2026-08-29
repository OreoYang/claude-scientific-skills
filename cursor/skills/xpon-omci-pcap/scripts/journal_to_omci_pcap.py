#!/usr/bin/env python3
"""Convert OLT journalctl/syslog OMCI transport hex dumps to Wireshark pcap.

Part of Cursor skill: xpon-omci-pcap (~/.cursor/skills/xpon-omci-pcap/).

OMCI frames are logged by bcm_omci_stack_util_dump_raw_buf() via omci-transport
(DEBUG). Each frame is a fake 14-byte Ethernet header (ethertype 0x88b5) plus OMCI.

Pcap packet timestamps are taken from the syslog/journal line of each frame's first
hex dump line (offset 0000). Syslog has no year; use --year or auto-detect ISO dates.

Requires vPONMgr log level: omci-transport = Debug.

Usage:
  python3 journal_to_omci_pcap.py journal.log -o omci.pcap
  python3 journal_to_omci_pcap.py journal.log -o omci.pcap --pon-ni 30 --onu-id 0
  journalctl --no-pager -n 50000 | python3 journal_to_omci_pcap.py - -o omci.pcap
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from pcap_ts import infer_year_from_text, parse_syslog_epoch, write_pcap

FRAME_KEY_RE = re.compile(
    r"\{olt_id=(?P<olt>\d+)\s+pon_if=(?P<pon>\d+),\s+onu_id=(?P<onu>\d+),\s+cookie=(?P<cookie>\d+)\}"
)
HEX_LINE_RE = re.compile(
    r"^(?P<offset>[0-9a-fA-F]{4,8})\s+(?P<bytes>(?:[0-9a-fA-F]{2}\s*)+)$"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="journal/messages log file or '-' for stdin")
    p.add_argument("-o", "--output", required=True, help="output .pcap path")
    p.add_argument("--pon-ni", type=int, default=None, help="filter logical PON (e.g. 30)")
    p.add_argument("--onu-id", type=int, default=None, help="filter ONU id (e.g. 0)")
    p.add_argument("--tail-lines", type=int, default=None, help="only use last N input lines")
    p.add_argument(
        "--year",
        type=int,
        default=None,
        help="calendar year for syslog lines without year (default: infer ISO date or current year)",
    )
    return p.parse_args()


def read_lines(path: str, tail_lines: int | None) -> list[str]:
    if path == "-":
        lines = sys.stdin.readlines()
    else:
        lines = Path(path).read_text(errors="replace").splitlines()
    if tail_lines is not None and tail_lines > 0:
        lines = lines[-tail_lines:]
    return lines


def line_frame_chunk(line: str) -> tuple[dict[str, int], int, bytes] | None:
    """Parse one journal/syslog line that contains OMCI hex dump."""
    m = FRAME_KEY_RE.search(line)
    if not m:
        return None
    pos = line.find("}: ", m.start())
    if pos < 0:
        return None
    tail = line[pos + 3 :].strip()
    parsed = hex_line_payload(tail)
    if not parsed:
        return None
    off, data = parsed
    meta = {
        "olt": int(m.group("olt")),
        "pon": int(m.group("pon")),
        "onu": int(m.group("onu")),
        "cookie": int(m.group("cookie")),
    }
    return meta, off, data


def hex_line_payload(line: str) -> tuple[int, bytes] | None:
    line = line.strip()
    m = HEX_LINE_RE.match(line)
    if not m:
        return None
    offset = int(m.group("offset"), 16)
    data = bytes(int(b, 16) for b in re.findall(r"[0-9a-fA-F]{2}", m.group("bytes")))
    return offset, data


def extract_packets(
    lines: list[str],
    pon_ni: int | None,
    onu_id: int | None,
    year: int,
) -> tuple[list[tuple[bytes, float | None]], int]:
    packets: list[tuple[bytes, float | None]] = []
    buf: dict[int, int] = {}
    cur_cookie: int | None = None
    frame_epoch: float | None = None
    skipped_filter = 0

    def flush() -> None:
        nonlocal buf, cur_cookie, frame_epoch
        if not buf:
            cur_cookie = None
            frame_epoch = None
            return
        max_off = max(buf)
        pkt = bytearray(max_off + 1)
        for off, val in buf.items():
            pkt[off] = val
        packets.append((bytes(pkt), frame_epoch))
        buf = {}
        cur_cookie = None
        frame_epoch = None

    for raw in lines:
        chunk = line_frame_chunk(raw)
        if chunk is None:
            continue

        meta, off, data = chunk
        if pon_ni is not None and meta["pon"] != pon_ni:
            skipped_filter += 1
            continue
        if onu_id is not None and meta["onu"] != onu_id:
            skipped_filter += 1
            continue

        if off == 0 and buf:
            flush()

        if cur_cookie is not None and meta["cookie"] != cur_cookie and off == 0:
            flush()

        if off == 0 or frame_epoch is None:
            frame_epoch = parse_syslog_epoch(raw, year)

        cur_cookie = meta["cookie"]
        for i, b in enumerate(data):
            buf[off + i] = b

    flush()
    return packets, skipped_filter


def main() -> int:
    args = parse_args()
    lines = read_lines(args.input, args.tail_lines)
    text = "\n".join(lines)
    year = args.year if args.year is not None else infer_year_from_text(text, datetime.now().year)
    packets, skipped = extract_packets(lines, args.pon_ni, args.onu_id, year)

    if not packets:
        print(
            "No OMCI frames found. Enable vPONMgr log: omci-transport = Debug, "
            "reproduce traffic, then retry.",
            file=sys.stderr,
        )
        if args.pon_ni is not None or args.onu_id is not None:
            print(
                f"Filter pon_ni={args.pon_ni} onu_id={args.onu_id} "
                f"skipped {skipped} frame headers.",
                file=sys.stderr,
            )
        return 1

    real_ts = write_pcap(args.output, packets)
    print(f"Wrote {len(packets)} packet(s) -> {args.output}")
    print(f"Timestamps: {real_ts}/{len(packets)} from log (syslog year={year})")
    if args.pon_ni is not None or args.onu_id is not None:
        print(f"Filter: pon_ni={args.pon_ni} onu_id={args.onu_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
