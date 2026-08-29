---
name: xpon-omci-pcap
description: >-
  Converts EXS1610 OLT journalctl/syslog OMCI transport hex dumps into Wireshark
  pcap files. Use when the user asks for OMCI pcap, Wireshark OMCI capture,
  journalctl to pcap, omci-transport log analysis, or decoding OMCI from OLT logs.
version: 1.0.0
---

# XPON OMCI journalctl → pcap

Generate Wireshark-ready `.pcap` from OLT `journalctl` or `/run/log/messages` when **omci-transport** debug logging is enabled.

**Bundled converters** (stdlib only; no pip deps):

| Script | Input format |
|--------|----------------|
| `scripts/journal_to_omci_pcap.py` | Linux `journalctl` / `messages` (`OMCI_TRANSPORT`, `pon_if=`) |
| `scripts/omft_vbuf_to_omci_pcap.py` | USR0-shell OMFT vbuf (`<OMCI MSG> Tx/Rx` + hex) |

**Pcap timestamps:** taken from the log line of each frame (syslog `Aug 4 05:54:10` or vbuf `21/07/70 17:36:48.943139`). Syslog has no year — use `--year 2026` or auto-detect ISO dates in the file. OMFT vbuf board dates like `21/07/70` use `--year` to set the calendar year (month/day/time from log).

**Related skills:** `xpon-chicago-lab-debug` (Chicago lab SSH/vPONMgr); `xpon-core-dump-debug` (crashes only).

---

## Agent workflow (execute, do not only document)

Copy this checklist and track progress:

```
- [ ] Step 1: Confirm omci-transport debug (or enable via vPONMgr)
- [ ] Step 2: Capture journalctl (preferred) or messages log
- [ ] Step 3: Run journal_to_omci_pcap.py → .pcap
- [ ] Step 4: Verify packet count > 0
- [ ] Step 5: Tell user pcap path + Wireshark plugin setup
```

### Step 1 — Enable OMCI hex logging

OMCI raw frames are logged by `bcm_omci_stack_util_dump_raw_buf()` from **omci-transport** only (`omci-me-layer` does **not** dump hex).

**vPONMgr** → OLT Logging Configuration:

| Log source | Level |
|------------|-------|
| `omci-transport` | **Debug** (required) |
| `omci-me-layer` | Debug (optional; ME text only) |
| `omci-svc` | Debug (optional) |

On the OLT node, sanity-check before capture:

```bash
journalctl --no-pager -n 200 | grep -m1 'pon_if='
# Expect: {olt_id=0 pon_if=30, onu_id=0, cookie=...}: 0000    00 18 48 ...
```

If zero matches: debug not active or no recent OMCI traffic — fix Step 1, reproduce flow create/delete, retry.

### Step 2 — Capture log

**Prefer `journalctl`** over `/run/log/messages` (messages is often rotated/truncated; journal retains OMCI hex).

```bash
# On OLT node
journalctl --no-pager -n 50000 > /tmp/omci-journal.log

# Or live window while user reproduces issue
journalctl -f -u netconf-polt | tee /tmp/omci-live.log
```

**Chicago SS2** (from dev machine):

```bash
sshpass -p '' ssh -T -o StrictHostKeyChecking=no root@10.254.20.137 \
  'journalctl --no-pager -n 50000' > /tmp/chicago-omci-journal.log
```

Optional time bounds:

```bash
journalctl --no-pager -u netconf-polt --since "10 min ago" > /tmp/omci-journal.log
```

### Step 3 — Convert to pcap

Run the bundled script (resolve path as `~/.cursor/skills/xpon-omci-pcap/scripts/journal_to_omci_pcap.py`).

```bash
SKILL_ROOT=~/.cursor/skills/xpon-omci-pcap
SCRIPT="$SKILL_ROOT/scripts/journal_to_omci_pcap.py"

# All ONUs in log
python3 "$SCRIPT" /tmp/omci-journal.log -o /tmp/omci-all.pcap

# Filter one ONU (Chicago PON16 XGS → pon_ni=30)
python3 "$SCRIPT" /tmp/omci-journal.log -o /tmp/omci-pon30-onu0.pcap \
  --pon-ni 30 --onu-id 0

# Pipe from SSH (one shot)
sshpass -p '' ssh -T root@10.254.20.137 'journalctl --no-pager -n 50000' | \
  python3 "$SCRIPT" - -o /tmp/omci-pon30-onu0.pcap --pon-ni 30 --onu-id 0
```

**Repo copy** (when working in `netconf-polt` tree):

```bash
python3 netconf-polt/scripts/messages_to_omci_pcap.py \
  /tmp/omci-journal.log -o /tmp/omci.pcap --pon-ni 30 --onu-id 0
```

### Step 4 — Verify output

Script prints `Wrote N packet(s) -> path`. If `N=0`:

1. Re-check Step 1 (`grep pon_if=` in journal).
2. Widen window: `-n 100000` or `--since`.
3. Remove `--pon-ni` / `--onu-id` filters to see if ONU id differs.

Quick packet count:

```bash
python3 -c "
import struct,sys
d=open(sys.argv[1],'rb').read(); i,n=24,0
while i+16<=len(d):
  l=struct.unpack('<I',d[i+8:i+12])[0]; n+=1; i+=16+l
print(n,'packets')
" /tmp/omci-pon30-onu0.pcap
```

### Step 5 — Wireshark

1. Install OMCI Lua dissector (once per machine):

```bash
mkdir -p ~/.local/share/wireshark/plugins
cp netconf-polt/third_party/omci-wireshark-dissector/omci.lua \
   ~/.local/share/wireshark/plugins/
# Or clone: https://github.com/0liv1er/omci-wireshark-dissector
```

2. Restart Wireshark.
3. Open `.pcap`. Display filter: `omci` or `eth.type == 0x88b5`.
4. Each packet = fake 14-byte Ethernet (ethertype `0x88b5`) + OMCI baseline/extended payload (as logged by OLT).

Details: [reference.md](reference.md)

---

## pon_ni quick map

| Physical PON | XGS `pon_ni` | GPON `pon_ni` |
|--------------|--------------|---------------|
| PON1 | 0 | 1 |
| PON16 | 30 | 31 |

Formula: XGS `pon_ni = (physical_port - 1) × 2`.

---

## Log line format (parser expectations)

Each OMCI frame spans multiple journal lines with the same `cookie`:

```text
... OMCI_TRANSPORT ... {olt_id=0 pon_if=30, onu_id=0, cookie=440}: 0000    00 18 48 ...
... OMCI_TRANSPORT ... {olt_id=0 pon_if=30, onu_id=0, cookie=440}: 000e    02 4D 44 ...
```

Parser rules:

- Reassemble by hex **offset** (`0000`, `000e`, …) until next offset `0000`.
- Filter by `--pon-ni` / `--onu-id` on the `{olt_id=… pon_if=…}` header.
- **Do not** use legacy `grep | sed` one-liners — they drop continuation lines and break frames.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `No OMCI frames found` | transport debug off or no traffic | vPONMgr omci-transport=Debug; reproduce OMCI |
| `messages` has 0 `pon_if=` | log only in journal | Use `journalctl`, not `tail messages` |
| pcap opens but no OMCI decode | Lua plugin missing | Install `omci.lua`; restart Wireshark |
| Wrong ONU in pcap | filter mismatch | Drop filters or check `pon_if` in raw log |
| Huge pcap | long journal window | `--tail-lines N` or `--since` narrower window |

---

## Publishing / sharing this skill

Ship the whole directory `xpon-omci-pcap/`:

```
xpon-omci-pcap/
├── SKILL.md
├── README.md
├── reference.md
└── scripts/
    └── journal_to_omci_pcap.py
```

Install: copy to `~/.cursor/skills/xpon-omci-pcap/` (personal) or `.cursor/skills/xpon-omci-pcap/` (project).
