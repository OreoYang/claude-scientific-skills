# OMCI pcap — technical reference

## Source code path (OLT)

Hex dumps are emitted by `bcm_omci_stack_util_dump_raw_buf()` in `netconf-polt/onu_mgmt/libomcistack/omci_stack_rx.c`.

Callers (when `ENABLE_LOG`):

| File | When |
|------|------|
| `omci_transport.c` | TX/RX OMCI message (uses `omci_transport_log_id`) |
| `omci_stack_api.c` | ME encode paths use `log_id_bcm_omci_stack_me_layer` → **suppressed** (no hex) |

Therefore only **OMCI_TRANSPORT** journal lines contain Wireshark hex.

## Frame layout in pcap

Each reassembled packet:

1. **14-byte synthetic Ethernet header**
   - Dst MAC: `00:18:48:00:00:00`
   - Src MAC: `00:18:48:<pon>:<onu_hi>:<onu_lo>` (from `logical_pon` + `onu_id`)
   - EtherType: `0x88b5`
2. **OMCI payload** (baseline 48 bytes or extended; as captured on wire)

Timestamps in pcap are synthetic (sequential microseconds); use journal line timestamps for real time correlation.

## Journal line anatomy

```text
Jul 25 06:05:02 chicago bcmolt_netconf_server[5911]: [pid: D OMCI_TRANSPORT] omci_stack_rx.c 1183| {olt_id=0 pon_if=30, onu_id=0, cookie=440}: 0000    00 18 48 00 00 00 00 18 48 1E 00 00 88 B5
```

| Field | Meaning |
|-------|---------|
| `pon_if` | BAL logical PON index (`pon_ni`) |
| `onu_id` | BAL ONU id |
| `cookie` | OMCI transaction cookie; lines with same cookie + increasing offset belong to one dump |
| `0000` / `000e` / … | Byte offset in reassembled packet |
| hex bytes | Data at that offset |

A new frame starts at offset `0000`. Prior buffer is flushed.

## Wireshark plugin

1. Copy `omci.lua` to `~/.local/share/wireshark/plugins/` (Linux) or `%APPDATA%\Wireshark\plugins` (Windows).
2. Wireshark ≥ 1.4.3, Lua ≥ 5.1.
3. Dissector registers on Ethernet type `0x88b5` and UDP (not used in this pcap path).

Upstream: https://github.com/0liv1er/omci-wireshark-dissector

In `netconf-polt`: `third_party/omci-wireshark-dissector/omci.lua`

## Useful Wireshark filters

| Filter | Use |
|--------|-----|
| `omci` | All decoded OMCI |
| `eth.type == 0x88b5` | Raw OMCI-over-Ethernet |
| `omci.msg_type == 8` | SET |
| `omci.msg_type == 9` | GET |
| `omci.msg_type == 6` | DELETE |

(Message type numbers per G.988; exact field name depends on dissector version.)

## Script CLI

```
journal_to_omci_pcap.py [-h] [-o OUTPUT] [--pon-ni N] [--onu-id N] [--tail-lines N] input

input: log file or '-' for stdin
```

Exit code `1` if no frames extracted.

## Chicago SS2 defaults

| Item | Value |
|------|-------|
| OLT | `root@10.254.20.137` (empty password) |
| vPONMgr | `10.254.21.43` |
| PON16 ALCL example | `--pon-ni 30 --onu-id 0` |

## Legacy anti-pattern (do not use)

Old wiki/skill snippets used:

```bash
grep omci_stack_rx | sed 's/^.*}: //g' > omci.pcap
```

Problems:

- `.pcap` is not valid binary (text hex only; needs converter)
- `sed` drops multi-line frame bodies
- `/run/log/messages` often lacks transport hex

Use `journal_to_omci_pcap.py` instead.
