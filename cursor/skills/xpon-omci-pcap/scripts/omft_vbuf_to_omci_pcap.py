#!/usr/bin/env python3
"""Convert Broadcom USR0-shell OMFT/OMCI vbuf trace to Wireshark OMCI pcap.

Input: dbg spt / OMFT vbuf capture (7360.txt style)
  [OMFT(vbuf):...]<OMCI MSG> Tx --> OntId(NG2) : 0 - ...
                     TCID / Action / ME / Inst
  [OMFT(vbuf):...]1a c4 49 0a 00 02 00 00
  00 00 00 00 00 00 00 00         ........
  ...

Pcap timestamps come from the OMFT/OMCI vbuf bracket time on the <OMCI MSG> line
(or the first hex line if the header line has no bracket timestamp).

Each OMCI baseline payload is wrapped in a fake 14-byte Ethernet header (ethertype 0x88b5)
for the omci.lua Wireshark dissector.

Usage:
  python3 omft_vbuf_to_omci_pcap.py 7360.txt -o 7360.pcap
  python3 omft_vbuf_to_omci_pcap.py 7360.txt -o 7360.pcap --pon-ni 30 --onu-id 0
  python3 omft_vbuf_to_omci_pcap.py 7360.txt -o 7360.pcap --year 2026
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

from pcap_ts import infer_year_from_text, parse_vbuf_epoch, write_pcap

OMCI_MSG_RE = re.compile(
    r"<OMCI MSG>\s*(?P<dir>Tx -->|Rx <--).*?OntId\([^)]*\)\s*:\s*(?P<onu>\d+)",
    re.IGNORECASE,
)
HEX_AFTER_BRACKET_RE = re.compile(
    r"\]\s*([0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2})*)"
)
HEX_LINE_RE = re.compile(
    r"^\s*([0-9a-fA-F]{2}(?:\s+[0-9a-fA-F]{2})*)(?:\s{2,}.*)?$"
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", help="OMFT vbuf log file")
    p.add_argument("-o", "--output", required=True, help="output .pcap path")
    p.add_argument("--pon-ni", type=int, default=30, help="PON NI for fake eth src (default 30)")
    p.add_argument("--onu-id", type=int, default=None, help="filter by OntId from log")
    p.add_argument(
        "--year",
        type=int,
        default=None,
        help="century base for vbuf DD/MM/YY dates (default: infer ISO date or current year)",
    )
    return p.parse_args()


def fake_ethernet(pon_ni: int, onu_id: int) -> bytes:
    hdr = bytearray(
        [
            0x00,
            0x18,
            0x48,
            0x00,
            0x00,
            0x00,
            0x00,
            0x18,
            0x48,
            0x00,
            0x00,
            0x01,
            0x88,
            0xB5,
        ]
    )
    hdr[9] = pon_ni & 0xFF
    hdr[10] = (onu_id // 0xFF) & 0xFF
    hdr[11] = onu_id % 0xFF
    return bytes(hdr)


def hex_from_line(line: str) -> bytes | None:
    m = HEX_AFTER_BRACKET_RE.search(line)
    if m:
        return bytes(int(b, 16) for b in m.group(1).split())
    m = HEX_LINE_RE.match(line)
    if m:
        return bytes(int(b, 16) for b in m.group(1).split())
    return None


def is_omci_meta_line(line: str) -> bool:
    return (
        "TCID :" in line
        or "Action :" in line
        or "ME :" in line
        or "Inst :" in line
        or "Result Reason :" in line
    )


def extract_frames(
    lines: list[str],
    pon_ni: int,
    onu_filter: int | None,
    year_override: int | None,
) -> list[tuple[bytes, float | None]]:
    packets: list[tuple[bytes, float | None]] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        m = OMCI_MSG_RE.search(line)
        if not m:
            i += 1
            continue

        onu_id = int(m.group("onu"))
        msg_epoch = parse_vbuf_epoch(line, year_override)

        if onu_filter is not None and onu_id != onu_filter:
            i += 1
            while i < n:
                if OMCI_MSG_RE.search(lines[i]):
                    break
                if hex_from_line(lines[i]) is not None:
                    i += 1
                    continue
                if lines[i].strip() == "":
                    i += 1
                    break
                if is_omci_meta_line(lines[i]):
                    i += 1
                    continue
                break
            continue

        i += 1
        while i < n and (lines[i].strip() == "" or is_omci_meta_line(lines[i])):
            i += 1

        omci = bytearray()
        while i < n:
            if OMCI_MSG_RE.search(lines[i]):
                break
            chunk = hex_from_line(lines[i])
            if chunk is None:
                if omci:
                    break
                if lines[i].strip() == "":
                    i += 1
                    break
                i += 1
                continue
            if not omci and msg_epoch is None:
                msg_epoch = parse_vbuf_epoch(lines[i], year_override)
            omci.extend(chunk)
            i += 1
            if lines[i - 1].strip() == "":
                break

        if omci:
            packets.append((fake_ethernet(pon_ni, onu_id) + bytes(omci), msg_epoch))

    return packets


def main() -> int:
    args = parse_args()
    text = Path(args.input).read_text(errors="replace")
    lines = text.splitlines()
    year_override = args.year if args.year is not None else infer_year_from_text(text, datetime.now().year)
    packets = extract_frames(lines, args.pon_ni, args.onu_id, year_override)

    if not packets:
        print("No OMCI MSG frames found in input.", file=sys.stderr)
        return 1

    real_ts = write_pcap(args.output, packets)
    print(f"Wrote {len(packets)} packet(s) -> {args.output}")
    print(f"Timestamps: {real_ts}/{len(packets)} from log (vbuf year={year_override})")
    if args.onu_id is not None:
        print(f"Filter: onu_id={args.onu_id} pon_ni={args.pon_ni} (eth header only)")
    else:
        print(f"pon_ni={args.pon_ni} for fake Ethernet header")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
