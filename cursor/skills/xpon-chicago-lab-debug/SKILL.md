---
name: xpon-chicago-lab-debug
description: >-
  English canonical; Chinese archive in SKILL.zh.md. Debug EXS1610 OLT on QD Chicago
  SS2 lab (10.254.20.137) and vPON Manager (vPM): SSH, DBC, BAL, journalctl,
  northbound Kafka/CPMP, Postgres. vPM may run as Docker Compose (Chicago ponmgr)
  or Nomad (container names like kafka-<alloc>). Use for Chicago lab, OLT node logs,
  vPM/Kafka telemetry, PON/ONU, EXS1610.
version: 1.4.0
---

# XPON Chicago Lab Debug Skill

Chinese version: `SKILL.zh.md` in this folder.

Chicago SS2 lab bench: OLT node debug is on `10.254.20.137`; northbound vPON Manager (vPM) is often on `10.254.21.43` (`chicago.vponmanager.qdlab`), or may be scheduled on another lab host via **Nomad**. For on-node work, SSH into the OLT first; Kafka / Postgres / UI run in containers on the vPM host (**Compose or Nomad**, see §13).

**Reference docs:**
- Lab topology / IPs: [QD-XGS-Chicago (SS2)](https://vecima.atlassian.net/wiki/spaces/PH/pages/137273176)
- General node debug: [5.2 Node Debug Methods](https://vecima.atlassian.net/wiki/spaces/TS/pages/169182158)
- Coredump analysis: use with the `xpon-core-dump-debug` skill

---

## 1. Lab quick reference (Chicago SS2)

| Device | IP / access | Account | Notes |
|------|-----------|------|------|
| **OLT Node (EXS1610)** | `10.254.20.137` (ma0) | `root` / **empty password** | SN `S220Z31018422`, device name `chicago` |
| Remote PC (console) | `10.254.20.184` | `root` / `vecima` | serial: `/dev/Node27` |
| EXC Chicago M OAM | `10.254.21.42` | CLI: `eacadmin/eacadmin` | NETCONF controller |
| **vPONMgr (vPM)** | `10.254.21.43` (mgmt `ens3`); FQDN `chicago.vponmanager.qdlab`; Kafka/OLT plane `31.27.90.100` (`ens8`) | SSH: `root` / `nokia@`; WebUI: `admin@vecima.com` / `Vecima@1234` | Docker compose PON Manager; Kafka + TimescaleDB; change log level, OMCI trace |
| APPS Chicago | `10.254.21.44` | `root` / `nokia@` | |

**VLANs:**
- Node DHCP: 991 | vCM: 955 | CPE traffic: 1410

**Chicago common PON / ONU (wiki config):**

| ONU | PON | SN | pon_ni (XGS) |
|-----|-----|-----|--------------|
| ONU1 | PON1 | ZYXE53725310 | 0 |
| ONU2 | PON1 | ZYXE537252FE | 0 |
| ONU5 | PON1 | HTSZ39003930 | 0 |
| ONU3 | PON16 | HTSZ260D9008 | 30 |
| ONU4 | PON16 | SCOMA120044C | 30 |

**pon_ni mapping (BAL):**
- `pon_ni = (physical PON port - 1) × 2` → XGS port (even)
- Example: PON1 → 0/1 (XGS/GPON), PON16 → 30/31

**channeltermination naming (common in logs):**
- Physical PON16 → `pon.16` (YANG name) → `pon_ni=30` (BAL XGS)

---

## 2. Log in to the node

### 2.1 SSH (preferred)

```bash
ssh root@10.254.20.137
# empty password, press Enter
```

After login the prompt looks like: `root@xgs1610:~ [A]#` (`[A]`/`[B]` are RAUC slots)

### 2.2 Via remote PC serial console

```bash
ssh root@10.254.20.184    # password vecima
minicom -w -D /dev/Node27
```

### 2.3 Quick health check (first thing after login)

```bash
cat /etc/os-release
partition-helper.py info
systemctl is-active netconf-polt netopeer2 protocol-handler lag dev_mgmt_daemon redis
uptime
```

---

## 3. Debug tool selection (decision tree)

```
What are you debugging?
├─ App layer (v-ani, forwarder, DHCP session, MAC table)
│   └─ dbc <app>                    ← preferred, Vecima DbgCli
├─ netconf-polt built-in Broadcom CLI (BAL API, OMCI)
│   └─ /opt/bcm68620/daemon_attach -global netconf
│       ⚠ mutually exclusive with dbc netconf
├─ BAL hardware (PON state, GEM, flow, ONU stats)
│   ├─ dump-stats.py                ← shortcut, recommended
│   └─ echo "..." | /opt/bcm68620/example_user_appl   ← one-shot
└─ dev_mgmt_daemon (BAL core daemon CLI)
    └─ /opt/bcm68620/daemon_attach -global dev_mgmt_daemon
```

| Tool | Path | Scope | Typical use |
|------|------|--------|----------|
| **dbc** | `/usr/bin/dbc` | Vecima app DbgCli | xpon objects, PH DHCP, LAG stats |
| **daemon_attach** | `/opt/bcm68620/daemon_attach` | BCM daemon FIFO CLI | netconf internal CLI, dev_mgmt |
| **example_user_appl** | `/opt/bcm68620/example_user_appl` | BAL interactive shell / pipe | Low-level PON/GEM/flow queries |
| **dump-stats.py** | `/usr/bin/dump-stats.py` | BAL stats wrapper | Quick dump pon/onu/gem/flow |

---

## 4. DBC (Debug Client)

### 4.1 Basic usage

```bash
dbc <app>                    # interactive mode
dbc -A <app>                 # same as above
dbc -C "<cmd>" -A <app>      # run one command and exit
# Ctrl+D to exit
# type help inside for all commands
```

### 4.2 Available app names

| dbc command | Service | Common debug |
|----------|------|------------|
| `dbc netconf` | netconf-polt | `xpon get vani all`, `l2_mac_table get` |
| `dbc ph` | protocol-handler | `showFwdInfo all`, `dumpDHCPSes`, `showAntiSpoofing all` |
| `dbc lag` | lag | `nni get <0..3>`, `inni get all`, `lag get 1` |
| `dbc node-mgr` | node-mgr | `serial`, `mac`, `get temp`, `get qsfp` |
| `dbc swm` | swmgr | `info` (dual-slot software info) |
| `dbc led-mgr` | led-mgr | `alarm_record` |
| `dbc metrics-mgr` | metrics-mgr | metrics related |
| `dbc sysmon` | sysmon | CPU/memory/disk |
| `dbc hwmon` | hwmon | Hardware monitoring |
| `dbc notif` | notif-mgr | Notifications |
| `dbc lldp-ctlr` | lldp-ctlr | LLDP |

App names are defined in `xpon-libs/debug/include/dbg.h` → `gAppList[]`.

### 4.3 Common netconf DBC commands

```bash
dbc netconf
help
xpon get vani all
xpon get channeltermination all
xpon get onus_onu all
l2_mac_table get
l2_mac_table dump
```

`xpon get <type> <name|all>` supported types:
`channelgroup|channelpair|channelpartition|channeltermination|wavelen_prof|hardware|ani|vani|ani_v-enet|enet|pots|gem|tcont|td_prof|classifier|policy|policy_profile|forwarder|onus_onu|...`

Handler implementation: `netconf-polt/netconf_server/modules/bbf-xpon/bbf-debug.c`

### 4.4 Common PH DBC commands

```bash
dbc ph
showDhcpv4Profile
showVlanSubItfCfg
showFwdInfo all
dumpDHCPSes
dumpDHCPV6Ses
showAntiSpoofing all
showDsFlooding all DHCPv4
pktCapture enable <filename> <count>   # DHCPv6 capture
pktCapture disable
```

Handler implementation: `xpon-apps/protocol-handler/common/src/ph_dbg.c`

### 4.5 LAG / INNI statistics

```bash
dbc lag
nni get 0              # uplink port 0..3
inni get all           # PON internal switch port
lag get 1
```

**PON ↔ INNI mapping:**

| PON Port | INNI ID |
|----------|---------|
| 0 | 6 |
| 1 | 7 |
| 2 | 4 |
| 3 | 5 |
| 4 | 2 |
| 5 | 3 |
| 6 | 0 |
| 7 | 1 |
| 8–15 | 8–15 |

---

## 5. daemon_attach

Attaches to a background BCM daemon CLI FIFO, for netconf-polt or dev_mgmt_daemon built-in CLI.

### 5.1 Usage

```bash
/opt/bcm68620/daemon_attach [-global] [-no-lineedit] [-path path] <daemon_name>
```

| Parameter | Meaning |
|------|------|
| `-global` | Single machine-wide daemon instance (**required on production nodes**) |
| `-no-lineedit` | Disable line editing (scripts / pipe use) |
| `-path path` | FIFO path, default `/tmp` |

### 5.2 Common daemon names

```bash
# netconf-polt built-in CLI (BAL host API, OMCI, …)
/opt/bcm68620/daemon_attach -global netconf

# BAL core daemon
/opt/bcm68620/daemon_attach -global dev_mgmt_daemon
```

Implementation: `netconf-polt/daemon/attach/bcmolt_daemon_attach.c`

### 5.3 Mutual exclusion with dbc

While `dbc netconf` is connected, `daemon_attach netconf` is blocked with:

> `dbc is active. Please exit dbc firstly if use daemon_attach!`

**Rule: Ctrl+D to exit dbc first, then daemon_attach.**

Source: `netconf-polt/netconf_server/bcmolt_netconf_server.c` → `DaemonCliThread()`

### 5.4 dbc vs daemon_attach comparison

| | dbc netconf | daemon_attach netconf |
|--|-------------|----------------------|
| Interface | Vecima DbgCli (xpon get, l2_mac_table) | Broadcom bcmcli (/a/g, /api/...) |
| Best for | YANG objects, application debug | Raw BAL API commands, scripted CLI |
| Exclusion | Mutually exclusive with daemon_attach | Mutually exclusive with dbc netconf |

---

## 6. BAL: example_user_appl

BAL interactive entry point at `/opt/bcm68620/example_user_appl`.

**Problem:** In interactive mode internal logs flood the screen and output is hard to read.

**Recommended:** Pipe one-shot commands with `echo`:

```bash
# PON1 (pon_ni=0) state
echo "/a/g object=pon_interface pon_ni=0 state" | /opt/bcm68620/example_user_appl

# PON1 active ONU count
echo "/a/g object=pon_interface pon_ni=0 number_of_active_onus" | /opt/bcm68620/example_user_appl

# PON16 (pon_ni=30)
echo "/a/g object=pon_interface pon_ni=30 state" | /opt/bcm68620/example_user_appl

# ONU state (PON1, onu_id=0)
echo "/a/g object=onu pon_ni=0 onu_id=0" | /opt/bcm68620/example_user_appl

# GEM list
echo "/a/m max_msgs=20 filter_invert=no object=itupon_gem pon_ni=0" | /opt/bcm68620/example_user_appl

# Flow list
echo "/a/m max_msgs=50 filter_invert=yes object=flow" | /opt/bcm68620/example_user_appl

# PON stats (do not clear counters)
echo "/a/t clear=no object=pon_interface sub=itu_pon_stats pon_ni=0" | /opt/bcm68620/example_user_appl

# uplink NNI stats
echo "/a/t clear=no object=nni_interface sub=stats id=0" | /opt/bcm68620/example_user_appl
```

You can also enter the interactive shell directly (type `quit` when done):

```bash
cd /opt/bcm68620 && ./example_user_appl
```

---

## 7. dump-stats.py (BAL stats shortcut)

```bash
dump-stats.py -h
dump-stats.py pon pon1
dump-stats.py pon pon16
dump-stats.py onu pon1
dump-stats.py onu pon16
dump-stats.py gem pon1
dump-stats.py tcont pon1
dump-stats.py flow
dump-stats.py nni
dump-stats.py tm_sched
dump-stats.py tm_queue
dump-stats.py inni pon1
```

Chicago common: `dump-stats.py pon pon1` / `dump-stats.py onu pon16`.

---

## 8. Log collection and analysis

### 8.1 Log locations

```bash
# unified syslog (preferred)
cat /run/log/messages
tail -F /run/log/messages
tail -500 /run/log/messages | grep -iE 'error|fail|segfault|critical|warn'

# systemd journal
journalctl --no-pager -n 200
journalctl -f
journalctl -p err..alert --since "1 hour ago" --no-pager
```

### 8.2 Filter by service

```bash
journalctl -u netconf-polt -b --no-pager | tail -100
journalctl -f -u netconf-polt
journalctl -f -u protocol-handler
journalctl -f -u lag
journalctl -f -u netopeer2
journalctl -f -u dev_mgmt_daemon
```

### 8.3 Key systemd units

| Unit | Role |
|------|------|
| `netconf-polt` | NETCONF/YANG, PON/ONU, OMCI |
| `protocol-handler` | DHCP/PPPoE/forwarding control |
| `lag` | Uplink NNI/LAG |
| `netopeer2` | NETCONF SSH server |
| `dev_mgmt_daemon` | BAL core daemon |
| `logsvr` | Centralized log receiver |
| `redis` | Internal KV (DHCP sessions, etc.) |
| `metrics-mgr` | Performance metrics |
| `event-monitor` | Event distribution |

### 8.4 Adjust log level

**vPONMgr:** WebUI Setting → Service Groups → OLT Logging Configuration
(or OLT Inventory → Configuration → Logging). SSH / Kafka / Postgres see **§13**.

Chicago wiki common debug sources:
- `omci-me-layer`, `omci-transport`, `omci-svc`, `netconf`, `bal-api` → debug

### 8.5 OMCI log → Wireshark pcap

**Use skill `xpon-omci-pcap`** (full workflow + `journal_to_omci_pcap.py` converter).

```bash
# 1. vPONMgr: omci-transport = Debug (required for hex frames)
# 2. Pull journal (prefer over /run/log/messages)
journalctl --no-pager -n 50000 > /tmp/omci-journal.log

# 3. Convert to pcap
python3 ~/.cursor/skills/xpon-omci-pcap/scripts/journal_to_omci_pcap.py \
  /tmp/omci-journal.log -o /tmp/omci.pcap --pon-ni 30 --onu-id 0
```

Wireshark: install `omci.lua` plugin; open `.pcap`; filter `omci` or `eth.type == 0x88b5`.

### 8.6 PLOAM log capture

```bash
# clear log (device_id=0 maps to pon_ni 0–15)
echo "/a/o object=log_file sub=clear device_id=0 file_id=ddr" | /opt/bcm68620/example_user_appl

# set debug level
echo "/a/s object=log device_id=0 name=ploam_us0 level={print=debug save=debug }" | /opt/bcm68620/example_user_appl
echo "/a/s object=log device_id=0 name=ploam_ds0 level={print=debug save=debug }" | /opt/bcm68620/example_user_appl

# dump
echo "user/read_embedded_logger device=0 file_id=ddr" | /opt/bcm68620/example_user_appl > /tmp/ploam.log

# restore info level
echo "/a/s object=log device_id=0 name=ploam_us0 level={print=info save=info }" | /opt/bcm68620/example_user_appl
echo "/a/s object=log device_id=0 name=ploam_ds0 level={print=info save=info }" | /opt/bcm68620/example_user_appl

# analyze
grep message_id /tmp/ploam.log
```

### 8.7 Support info archive

```bash
ls /tmp/debug/support-info-logs*.tar.gz
# coredump decrypt → xpon-core-dump-debug skill
```

### 8.8 Fiber pull/insert / indication test log capture

When an agent or a human runs a test, start a background `netconf-polt` journal capture on the node, then pull logs to the dev machine for analysis.

**Start capture on the node:**

```bash
CAP=/tmp/fiber_test_capture.log
date "+%Y-%m-%d %H:%M:%S" > /tmp/fiber_test_start.txt
echo "=== START $(cat /tmp/fiber_test_start.txt) ===" >> "$CAP"
nohup journalctl -f -u netconf-polt -o short-precise >> "$CAP" 2>&1 &
echo $! > /tmp/fiber_test_jpid
```

**Stop and pull after the test (dev machine, needs sshpass):**

```bash
sshpass -p '' ssh root@10.254.20.137 'kill $(cat /tmp/fiber_test_jpid) 2>/dev/null'
sshpass -p '' scp root@10.254.20.137:/tmp/fiber_test_capture.log ./fiber_test.log
sshpass -p '' scp root@10.254.20.137:/tmp/fiber_test_start.txt ./marker.txt
```

**Analysis keywords (fiber pull/insert):**

```bash
grep -iE "pon_interface LOS|LOS status|indication '|deactivation|activation|ranging|online_onus|notif_mgr|alarm_id" fiber_test.log \
  | grep -v "ONU_discovered: onu_id=65535"
```

---

## 9. NETCONF / Sysrepo (config-side debug)

```bash
# local NETCONF client
netopeer2-cli
> connect --port 830 --host 127.0.0.1 --login root

# read datastore directly
sysrepocfg -d running -X
sysrepocfg -d operational -X
sysrepocfg -d running -m bbf-xpon -X

# software / partition
partition-helper.py info
rauc status --detailed
```

---

## 10. Common troubleshooting flows

### 10.1 ONU not coming online

```bash
systemctl status netconf-polt dev_mgmt_daemon --no-pager
echo "/a/g object=pon_interface pon_ni=0 state" | /opt/bcm68620/example_user_appl
dump-stats.py pon pon1
dbc -C "xpon get vani all" -A netconf
journalctl -u netconf-polt --since "10 min ago" --no-pager | grep -i omci
```

### 10.2 DHCP not working

```bash
dbc -C "dumpDHCPSes" -A ph
dbc -C "showFwdInfo all" -A ph
dbc -C "showVlanSubItfCfg" -A ph
journalctl -u protocol-handler --since "10 min ago" --no-pager
```

### 10.3 netconf-polt crash / SIGSEGV

```bash
journalctl -u netconf-polt -b --no-pager | tail -50
ls -la /tmp/debug/ /var/lib/systemd/coredump/
# → xpon-core-dump-debug skill
```

### 10.4 Replace binary (development iteration)

On EXS1610, `usr.mount` mounts `/usr` read-only by default (RAUC rootfs overlay). **Direct scp to `/usr/bin/` fails**; you must disable `usr.mount` and reboot first; after reboot `/usr` is writable.

#### Procedure (on the node)

```bash
# 1. log in to node
ssh root@10.254.20.137

# 2. disable usr.mount (writable /usr on next boot)
systemctl disable usr.mount

# 3. reboot (required after disable)
reboot
```

#### After reboot completes (scp from dev machine)

```bash
# 4. after node is up, scp (do not scp before reboot)
sshpass -p '' scp <path>/bcmolt_netconf_server root@10.254.20.137:/usr/bin/bcmolt_netconf_server

# 5. restart service and verify
sshpass -p '' ssh root@10.254.20.137 \
  "chmod 755 /usr/bin/bcmolt_netconf_server && systemctl restart netconf-polt.service && systemctl status netconf-polt.service --no-pager"
sshpass -p '' ssh root@10.254.20.137 "dbc -C help -A netconf"   # should print Usage, not SIGSEGV
```

#### Local artifact path

```bash
cd ~/works/repo && . setup-env
bitbake netconf-polt -c compile -f
find ~/works/repo/build-xpon/tmp/work -path '*netconf-polt*' -name bcmolt_netconf_server
```

#### Notes

| Step | Explanation |
|------|------|
| `systemctl disable usr.mount` | **Do this first**, or `/usr` stays read-only |
| `reboot` | **Required after disable**; scp only works after reboot |
| scp timing | **After reboot completes**; do not scp between disable and reboot |
| Full image upgrade | Production / formal validation uses RAUC bundle, not this dev flow |
| scp tool | On dev machine use `sshpass -p '' scp ...` (see §11.2) |

### 10.5 Fiber pull/insert — indications triggered (Chicago PON16 measured)

Physical PON16 (`pon_ni=30`, `pon.16`), typical sequence for one fiber pull with 2 ONUs online.

**Pull fiber (LOS ON):**

| Order | Indication / event | Module |
|------|-------------------|------|
| 1 | `pon_interface LOS` status=ON | `bbf-xpon.c` `_pon_interface_indication_cb` |
| 2 | PON LOS alarm report (alarm_id=50, `is_clear:false`) | `ipc-notif-mgr.c` |
| 3 | `pon_interface LOS status is on` | `bbf-xpon.c` |
| 4 | ONU audit debounce cleared | `bbf-xpon-v-ani.c` |
| 5 | `onu_deactivation_completed` (each online ONU) | `bbf-xpon-v-ani.c` |
| 6 | Remove from `online_onus` + v-ani → `onu-not-present-with-v-ani` | `bbf-xpon-channel-termination.c` |
| 7 | `ipc_notif_mgr_send_onu_presence` | `ipc-notif-mgr.c` |
| 8 | OMCI deactivate + `_onualarm_clearall` (reason=LOS) | `omci_svc` / `bbf-xpon-v-ani.c` |

**Re-insert fiber (recovery):**

| Order | Indication / event | Notes |
|------|-------------------|------|
| 1 | `pon_interface LOS` status=OFF | May be skipped when `online_onus` empty: `LOS OFF is not reasonable` |
| 2 | `ONU_discovered` | Once per ONU |
| 3 | `ranging_completed` | |
| 4 | `onu_activation_completed` | |
| 5 | OMCI activate starts | |
| 6 | `onu-present` presence notify may be skipped | Flap protection |
| 7 | OMCI UNI link-down alarm (id=41) then clear | Ethernet port state, not PON LOS |

**~10s later (LOS WA timer):**

| Event | Explanation |
|------|------|
| `_cterm_pon_los_check_timeout_handler` | Workaround for inconsistent BAL LOS-OFF behavior; clears PON LOS alarm (`is_clear:true`) |

**Indications not seen this time:** Per-ONU XGPON PHY alarms (`looci`/`dowi`/`dgi`, etc.) — LOS path bulk-deactivates ONUs without the single-ONU PHY alarm branch.

Source anchors:
- PON LOS: `netconf-polt/netconf_server/modules/bbf-xpon/bbf-xpon.c` → `BCMOLT_PON_INTERFACE_AUTO_SUBGROUP_LOS`
- LOS WA timer: `bbf-xpon-channel-termination.c` → `_cterm_pon_los_check_timeout_handler` (10s)
- ONU indication: `bbf-xpon-v-ani.c` → `_onu_indication_cb`

---

## 11. Agent / local PC remote SSH

Chicago OLT: `root@10.254.20.137`, **empty password**.

### 11.1 Manual SSH (terminal)

```bash
ssh root@10.254.20.137    # empty password at prompt, press Enter
```

### 11.2 sshpass (agent / scripted SSH)

**Install on: local PC / LXD dev container** (not on the OLT). `sshpass` is an SSH **client** tool; install it on the side that initiates the connection.

Vecima LXD container (vcmos 5.0) dnf repos **do not** ship `sshpass`; build from source:

```bash
# inside LXD container (needs gcc/make/curl)
cd /tmp
curl -fsSL -o sshpass-1.10.tar.gz \
  https://downloads.sourceforge.net/project/sshpass/sshpass/1.10/sshpass-1.10.tar.gz
tar xzf sshpass-1.10.tar.gz && cd sshpass-1.10
./configure --prefix=$HOME/.local && make -j$(nproc) && make install

# verify
sshpass -V
sshpass -p '' ssh -o StrictHostKeyChecking=no root@10.254.20.137 'hostname'
```

Install path: `~/.local/bin/sshpass` (oreo user PATH already includes `~/.local/bin`).

**Ubuntu LXD host** can use: `sudo apt install sshpass`

### 11.3 Agent auto-connect to OLT examples

```bash
sshpass -p '' ssh root@10.254.20.137 'journalctl -u netconf-polt -n 50 --no-pager'
sshpass -p '' scp root@10.254.20.137:/run/log/messages /tmp/olt-messages.log
```

### 11.4 Alternative: SSH public-key login

Copy local `~/.ssh/id_ed25519.pub` to OLT `/root/.ssh/authorized_keys`; then sshpass is not needed.

### 11.5 Prerequisites for agent remote operations

- `~/.local/bin/sshpass` installed and verified (§11.2) → agent can auto SSH/scp to Chicago OLT (empty password) and vPM (`nokia@`, §13)
- If not installed: user SSHs manually in a terminal, or pastes logs / scp files for the agent to analyze

---

## 12. Hardware / manufacturing info

```bash
onie-syseeprom
cat /run/dev/rip/serial-num
cat /run/dev/rip/mac-base
sensors
dbc -C "get hwmonall" -A node-mgr
```

---

## 13. Chicago vPON Manager (vPM) debug

Northbound controller: **Kafka broker runs on the vPM host, not on the OLT.** OLT `metrics-mgr` / `notif-mgr` are Kafka producers.

### 13.0 Compose vs Nomad (identify deployment first)

| Trait | Docker Compose (classic Chicago) | Nomad + Docker driver (common newer labs) |
|------|-------------------------------|-------------------------------------|
| Container names | `ponmgr-kafka-1`, `ponmgr-postgresql-1` | `<task>-<alloc-id>`, e.g. `kafka-27bf8e79-…`, `postgres-9b997f21-…` |
| Management | `docker compose -f …/docker-compose.yml ps` | `nomad job status` / `nomad alloc status <id>`; still use **`docker ps`** on the client to see containers |
| Paths | `/root/workspace/pon-mgr-deploy/docker-compose` | No fixed compose dir; data volumes mounted by Nomad |
| Microservice prefix | `ponmgr-ponmgrltcs-1` | `ponmgrltcs-<alloc>`, `ponmgrprov-<alloc>`, `ponmgrctrl-<alloc>` |

**Agent rule:** Do not hard-code `ponmgr-kafka-1`. Run `docker ps --format '{{.Names}}'`, resolve containers by **service name prefix**, then `docker exec`.

On the vPM **host** shell, load once (works for Compose and Nomad):

```bash
# Usage: vpm_ctnr kafka | postgres | ponmgradb | redis | ponmgrltcs | ponmgrprov | ponmgrctrl | ponmgrui
vpm_ctnr() {
  local svc="$1"
  case "$svc" in
    kafka)       docker ps --format '{{.Names}}' | grep -E '^kafka-' | head -1 ;;
    postgres)    docker ps --format '{{.Names}}' | grep -E '^postgres-' | head -1 ;;
    ponmgradb)   docker ps --format '{{.Names}}' | grep -E '^ponmgradb-' | head -1 ;;
    redis)       docker ps --format '{{.Names}}' | grep -E '^redis-' | head -1 ;;
    ponmgrltcs)  docker ps --format '{{.Names}}' | grep -E '^ponmgrltcs-' | head -1 ;;
    ponmgrprov)  docker ps --format '{{.Names}}' | grep -E '^ponmgrprov-' | head -1 ;;
    ponmgrctrl)  docker ps --format '{{.Names}}' | grep -E '^ponmgrctrl-' | head -1 ;;
    ponmgrui)    docker ps --format '{{.Names}}' | grep -E '^ponmgrui-' | head -1 ;;
    *) echo "unknown svc: $svc" >&2; return 1 ;;
  esac
}

# Compose fallback (Chicago only): if vpm_ctnr kafka is empty, try ponmgr-kafka-1
vpm_kafka() { vpm_ctnr kafka || echo ponmgr-kafka-1; }
vpm_pg()    { vpm_ctnr postgres || vpm_ctnr ponmgradb || echo ponmgr-postgresql-1; }

# Kafka CLI path depends on image (do not assume /opt/kafka/bin only)
#   apache/kafka (Compose Chicago):  /opt/kafka/bin/kafka-topics.sh
#   vecima-registry kafka (Nomad): /usr/bin/kafka-topics.sh  (symlink → ../share/kafka/bin/)
kafka_topics_sh() {
  local k="${1:-$(vpm_kafka)}"
  docker exec "$k" sh -c 'test -x /usr/bin/kafka-topics.sh && echo /usr/bin/kafka-topics.sh || echo /opt/kafka/bin/kafka-topics.sh'
}
```

Nomad stacks often also have observability components (not required for Kafka debug): `grafana-`, `loki-`, `tempo-`, `otelcol-`, `victoria-metrics-`, `nginx-`, `registry-`, `evc-`, etc.

**Chicago Compose** reference: hostname `chicago.vponmanager.qdlab`, RHEL 9.4, project `ponmgr`, image tag `390`, directory `/root/workspace/pon-mgr-deploy/docker-compose`.

### 13.1 Login

```bash
# SSH (agent / scripts)
sshpass -p 'nokia@' ssh -o StrictHostKeyChecking=no root@10.254.21.43
# or
ssh root@chicago.vponmanager.qdlab    # password nokia@

# WebUI
# https://10.254.21.43:8443  or  http://10.254.21.43:8080
# admin@vecima.com / Vecima@1234
```

| Plane | Address | Purpose |
|----|------|------|
| mgmt `ens3` | `10.254.21.43/23` | SSH, WebUI, lab management network |
| Kafka/OLT `ens8` | `31.27.90.100/24` | OLT northbound to Kafka SSL (Chicago OLT `31.27.60.59` → `:10096`) |
| docker0 / compose | `172.17.0.1` / `172.18.0.1` | Container interconnect (`kafka:9092`, `postgresql:5432`) |

### 13.2 Stack overview

```
OLT metrics-mgr  --TLS produce-->  vPM Kafka (1 broker, KRaft)
        |  vecima-olt-telemetry, cpmp-olt-telemetry, XGS-Alarms
        v
   ponmgrltcs (consumer group ponltcs)  -->  PostgreSQL / TimescaleDB
```

**Inventory (any deployment):**

```bash
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
# Compose only:
test -f /root/workspace/pon-mgr-deploy/docker-compose/docker-compose.yml && \
  docker compose -f /root/workspace/pon-mgr-deploy/docker-compose/docker-compose.yml ps
# Nomad only (on client or server with CLI):
nomad job status 2>/dev/null | head -30
```

| Logical service | Compose container | Nomad container prefix (example) | Role |
|----------|----------------|--------------------------|------|
| Kafka | `ponmgr-kafka-1` | `kafka-<alloc>` | Single broker; OLT SSL northbound |
| Postgres / Timescale | `ponmgr-postgresql-1` | `postgres-<alloc>` or `ponmgradb-<alloc>` | App DBs (`ponmgrltcs`, `ponmgrprov`, …) |
| Redis | `ponmgr-redis-1` | `redis-<alloc>` | Cache |
| Analytics | `ponmgr-ponmgrltcs-1` | `ponmgrltcs-<alloc>` | Consumes `vecima-olt-telemetry`, etc. |
| Control | `ponmgr-ponmgrctrl-1` | `ponmgrctrl-<alloc>` | Call Home / control plane |
| Provisioning | `ponmgr-ponmgrprov-1` | `ponmgrprov-<alloc>` | OLT provisioning |
| UI | `ponmgr-ponmgrui-1` | `ponmgrui-<alloc>` | Web UI (often behind `nginx-<alloc>`) |
| Grafana / Loki | `ponmgr-grafana-1` | `grafana-<alloc>`, `loki-<alloc>` | Logs / metrics dashboards |

Compose volumes: `ponmgr_kafka_data`, `ponmgr_postgres_data`. Nomad: check alloc mounts (`nomad alloc status -verbose <alloc>`) or host `df` / volume paths.

### 13.3 Kafka (single broker)

**Chicago lab has 1 Kafka broker** (one container). It is not a process on the OLT.

| Container port | Host | Protocol | advertised | Used by |
|----------|--------|------|------------|--------|
| 9092 | **10092** | PLAINTEXT `CLIENT` | `kafka:9092` | Compose internal microservices |
| 9093 | 10093 | PLAINTEXT `EXTERNAL` | `localhost:10093` | Local debug on host |
| 9094 | 10094 | `CONTROLLER` | (KRaft internal) | **Do not use as client port** |
| 9096 | **10096** | **SSL `SECURE`** | `chicago.vponmanager.qdlab:10096` | **OLT telemetry / alarms** |

OLT YANG (measured running):

```xml
<address>chicago.vponmanager.qdlab</address>
<remote-port>10096</remote-port>
<publish-timer>120</publish-timer>
```

TLS is on **10096**, not YANG default 9094, and not host 10094 (controller).

```bash
# On vPM host — use vpm_kafka() from §13.0 (or ponmgr-kafka-1 on Compose)
K="$(vpm_kafka)"
KT="$(kafka_topics_sh "$K")"
docker exec "$K" "$KT" --bootstrap-server localhost:9092 --list

docker exec "$K" "$KT" --bootstrap-server localhost:9092 --describe --topic vecima-olt-telemetry

docker exec "$K" "$KT" --bootstrap-server localhost:9092 --describe --topic cpmp-olt-telemetry

docker exec "$K" /usr/bin/kafka-get-offsets.sh \
  --bootstrap-server localhost:9092 --topic vecima-olt-telemetry --time -1

docker exec "$K" /usr/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 --group ponltcs --describe

docker logs --tail 80 "$K"
```

**CPMP `Local: Unknown topic` on OLT:** usually **topic missing on broker** (not OLT `/` disk). If `vecima-olt-telemetry` exists but `cpmp-olt-telemetry` does not, create it (match partitions/RF of vecima topic):

```bash
K="$(vpm_kafka)"
KT="$(kafka_topics_sh "$K")"
docker exec "$K" "$KT" --bootstrap-server localhost:9092 \
  --create --if-not-exists --topic cpmp-olt-telemetry --partitions 1 --replication-factor 1
```

If Kafka **broker disk** is full, check the **Nomad client / volume** backing `kafka-*`, not the OLT root filesystem.

OLT-side topics: `vecima-olt-telemetry` (metrics-mgr tier), `cpmp-olt-telemetry` (CPMP sink), `XGS-Alarms` (notif-mgr). `ponltcs` consumes telemetry; **lag should be 0** when Analytics is keeping up.

Verify connection on OLT:

```bash
sysrepocfg -X -d running -f xml -x /vecima-device:device/kafka-interface
netstat -tn | grep 10096
systemctl is-active metrics-mgr
journalctl -u metrics-mgr -n 50 --no-pager | grep -iE 'broker|Kafka producer|reconnect'
```

### 13.4 Storage: PostgreSQL + TimescaleDB (it is Postgres)

Postgres container: `ponmgr-postgresql-1` (Compose) or `postgres-*` / `ponmgradb-*` (Nomad). Usually **PostgreSQL 15** + **TimescaleDB**. App databases are split per microservice; **not** Mongo/MySQL.

| Database | Owner / service | Stores |
|----|----------------|--------|
| `ponmgrltcs` | Analytics (`ponmgrltcs`) | Telemetry: `channel_termination_statsv3`, `lag_statsv2`, `dhcpv4_stats`, `onu_rssi`, `transceiver_*`, `l2_forwarding`, `lldp`, etc. |
| `ponmgrprov` | provisioning | OLT/ONU/subscriber; Chicago table names use `_chicago` (e.g. `olt`, `onu`, `alarmsv2_chicago`) |
| `ponmgrauth` | auth | users / operators / tokens |
| `ponmgrfms` | firmware | ONU/OLT firmware, campaigns |
| `ponmgrrbac` | RBAC | roles / policies |
| `ponmgrsupinfo` | support-info | support package metadata |
| `postgres` | superuser | maintenance DB |

Use superuser inside the container; no need to dig app passwords from `.env`:

```bash
PG="$(vpm_pg)"
docker exec -it "$PG" psql -U postgres
# \l
# \c ponmgrltcs
# \dt
# SELECT COUNT(*) FROM channel_termination_statsv3;
# \c ponmgrprov
# SELECT * FROM olt;
```

Non-interactive:

```bash
PG="$(vpm_pg)"
docker exec "$PG" psql -U postgres -c '\l'
docker exec "$PG" psql -U postgres -d ponmgrltcs -c '\dt'
docker exec "$PG" pg_isready -U postgres
```

Compose backup: `/root/workspace/pon-mgr-deploy/docker-compose/db-backup.sh` / `db-restore.sh`. Nomad: follow platform runbook or volume snapshot.

Redis is session/cache, **not** primary telemetry storage. Kafka is the pipe; **persistence is Postgres (Timescale)**.

### 13.5 Microservice logs / Grafana

```bash
docker logs --tail 100 "$(vpm_ctnr ponmgrltcs || echo ponmgr-ponmgrltcs-1)"
docker logs --tail 100 "$(vpm_ctnr ponmgrctrl || echo ponmgr-ponmgrctrl-1)"
docker logs --tail 100 "$(vpm_pg)"
```

Grafana: Compose often `http://<vpm-host>:3000`; Nomad often `grafana-<alloc>` (port from `docker ps` / ingress). WebUI OLT log level changes still use §8.4.

### 13.6 Agent remote vPM

```bash
# Replace host/user/password for your Nomad client
sshpass -p 'nokia@' ssh -o StrictHostKeyChecking=no root@10.254.21.43 \
  'docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "kafka-|postgres-|ponmgr"'
```

Nomad one-liner from dev PC (after SSH to vPM host):

```bash
K=$(docker ps --format '{{.Names}}' | grep -E '^kafka-' | head -1)
docker exec "$K" /usr/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

BusyBox is not on vPM (RHEL); on OLT use `head -n N`, not `head -40`.

---

## Quick Reference Card

```bash
# login
ssh root@10.254.20.137          # empty password

# health
systemctl is-active netconf-polt protocol-handler lag dev_mgmt_daemon
cat /etc/os-release

# app debug
dbc netconf                     # xpon get vani all
dbc ph                          # dumpDHCPSes
dbc lag                         # inni get all

# BAL debug
dump-stats.py pon pon1
echo "/a/g object=pon_interface pon_ni=0 state" | /opt/bcm68620/example_user_appl

# netconf built-in CLI (exit dbc netconf first)
/opt/bcm68620/daemon_attach -global netconf

# Log
tail -F /run/log/messages
journalctl -f -u netconf-polt
journalctl -p err..alert --since "1 hour ago" --no-pager

# replace binary (disable usr.mount + reboot first, then scp)
sshpass -p '' ssh root@10.254.20.137 "systemctl disable usr.mount && reboot"
# after node is up:
sshpass -p '' scp <path>/bcmolt_netconf_server root@10.254.20.137:/usr/bin/
sshpass -p '' ssh root@10.254.20.137 "chmod 755 /usr/bin/bcmolt_netconf_server && systemctl restart netconf-polt"

# fiber pull/insert log capture (§8.8 / §10.5)

# --- vPM (host varies; Chicago 10.254.21.43 password nokia@) ---
sshpass -p 'nokia@' ssh root@10.254.21.43
docker ps --format '{{.Names}}' | grep -E '^kafka-|^postgres-|^ponmgr'
K=$(docker ps --format '{{.Names}}' | grep -E '^kafka-' | head -1)
docker exec "$K" /usr/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
PG=$(docker ps --format '{{.Names}}' | grep -E '^postgres-' | head -1); docker exec "$PG" psql -U postgres -c '\l'
# OLT kafka-interface → vPM FQDN + SSL port (Chicago: chicago.vponmanager.qdlab:10096)
```
