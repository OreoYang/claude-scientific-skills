# xpon-omci-pcap

Cursor Agent Skill: convert EXS1610 OLT **journalctl** / syslog OMCI transport hex dumps into **Wireshark pcap** files.

## Install

**One-liner** (from this directory):

```bash
./install.sh
# or project-local:
./install.sh /path/to/your-repo/.cursor/skills/xpon-omci-pcap
```

**Manual:**

```bash
cp -r xpon-omci-pcap ~/.cursor/skills/
chmod +x ~/.cursor/skills/xpon-omci-pcap/scripts/journal_to_omci_pcap.py
```

Or symlink:

```bash
ln -s /path/to/xpon-omci-pcap ~/.cursor/skills/xpon-omci-pcap
```

## Distribute to team

1. Zip or copy the whole `xpon-omci-pcap/` folder (no extra deps).
2. Each developer runs `./install.sh` or copies into `~/.cursor/skills/`.
3. Optional: commit under repo `.cursor/skills/xpon-omci-pcap/` for project-wide use.

```bash
tar czf xpon-omci-pcap-1.0.0.tar.gz xpon-omci-pcap/
```

## Quick start

```bash
# 1. vPONMgr: omci-transport = Debug
# 2. Pull journal from OLT
ssh root@10.254.20.137 'journalctl --no-pager -n 50000' > omci-journal.log

# 3. Convert
python3 ~/.cursor/skills/xpon-omci-pcap/scripts/journal_to_omci_pcap.py \
  omci-journal.log -o omci.pcap --pon-ni 30 --onu-id 0

# 4. Wireshark + omci.lua plugin
wireshark omci.pcap
```

## Contents

| File | Purpose |
|------|---------|
| `SKILL.md` | Agent instructions (Cursor skill entry point) |
| `reference.md` | Log format, frame layout, Wireshark notes |
| `scripts/journal_to_omci_pcap.py` | Stdlib-only converter (no pip) |

## Requirements

- Python 3.8+
- OLT: `omci-transport` log level **Debug** (vPONMgr)
- Wireshark + [omci-wireshark-dissector](https://github.com/0liv1er/omci-wireshark-dissector) Lua plugin for decode

## License

Converter script: same license as parent XPON project. OMCI dissector: GPLv2 (see upstream repo).
