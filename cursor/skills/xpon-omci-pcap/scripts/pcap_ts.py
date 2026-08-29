"""Parse log-line timestamps and write pcap with real epoch times."""

from __future__ import annotations

import re
import struct
from datetime import datetime
from pathlib import Path

SYSLOG_TS_RE = re.compile(
    r"(?P<mon>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<hms>\d{2}:\d{2}:\d{2})"
)

ISO_DATE_RE = re.compile(r"(?P<y>20\d{2})-(?P<m>\d{2})-(?P<d>\d{2})")

VBUF_TS_RE = re.compile(
    r"\[(?:OMFT|OMCI)\(vbuf\):\d+\s+"
    r"(?P<dmy>\d{2}/\d{2}/\d{2})\s+"
    r"(?P<hms>\d{2}:\d{2}:\d{2})\.(?P<usec>\d+)\s*\]"
)


def infer_year_from_text(text: str, default_year: int) -> int:
    m = ISO_DATE_RE.search(text)
    if m:
        return int(m.group("y"))
    return default_year


def expand_two_digit_year(yy: int, base_century_year: int | None) -> int:
    if yy >= 100:
        return yy
    if base_century_year is not None:
        return (base_century_year // 100) * 100 + yy
    return 2000 + yy if yy < 70 else 1900 + yy


def parse_syslog_epoch(line: str, year: int) -> float | None:
    m = SYSLOG_TS_RE.search(line)
    if not m:
        return None
    dt = datetime.strptime(
        f"{m.group('mon')} {int(m.group('day'))} {m.group('hms')} {year}",
        "%b %d %H:%M:%S %Y",
    )
    return dt.timestamp()


def parse_vbuf_epoch(line: str, year_override: int | None = None) -> float | None:
    m = VBUF_TS_RE.search(line)
    if not m:
        return None
    day_s, month_s, year_s = m.group("dmy").split("/")
    if year_override is not None:
        year = year_override
    else:
        year = expand_two_digit_year(int(year_s), None)
    dt = datetime(
        year,
        int(month_s),
        int(day_s),
        int(m.group("hms")[0:2]),
        int(m.group("hms")[3:5]),
        int(m.group("hms")[6:8]),
        int(m.group("usec")[:6].ljust(6, "0")[:6]),
    )
    return dt.timestamp()


def epoch_to_pcap_ts(epoch: float) -> tuple[int, int]:
    if epoch < 0:
        epoch = 0.0
    ts_sec = int(epoch)
    ts_usec = int(round((epoch - ts_sec) * 1_000_000))
    if ts_usec >= 1_000_000:
        ts_sec += 1
        ts_usec -= 1_000_000
    return ts_sec, ts_usec


def write_pcap(path: str, packets: list[tuple[bytes, float | None]]) -> int:
    """Write pcap; returns count of packets that used a real log timestamp."""
    gh = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    last_epoch: float | None = None
    fallback_epoch = 0.0
    real_ts_count = 0

    with out.open("wb") as f:
        f.write(gh)
        for pkt, epoch in packets:
            if epoch is not None:
                last_epoch = epoch
                real_ts_count += 1
                ts_sec, ts_usec = epoch_to_pcap_ts(epoch)
            elif last_epoch is not None:
                last_epoch += 1e-6
                ts_sec, ts_usec = epoch_to_pcap_ts(last_epoch)
            else:
                ts_sec, ts_usec = epoch_to_pcap_ts(fallback_epoch)
                fallback_epoch += 1e-6

            incl_len = len(pkt)
            ph = struct.pack("<IIII", ts_sec, ts_usec, incl_len, incl_len)
            f.write(ph)
            f.write(pkt)

    return real_ts_count
