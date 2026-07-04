---
name: xpon-chicago-lab-debug
description: >-
  Debug EXS1610 OLT on QD Chicago SS2 lab (10.254.20.137): SSH login, DBC,
  daemon_attach, BAL example_user_appl, dump-stats.py, journalctl log analysis.
  Use when debugging Chicago lab, OLT node logs, PON/ONU issues, or EXS1610
  runtime diagnostics on 10.254.20.137.
version: 1.1.0
---

# XPON Chicago Lab Debug Skill

Chicago SS2 实验台 OLT 节点调试工作流。所有 node 内 debug 操作需先进入 node shell。

**参考文档：**
- Lab 拓扑/IP：[QD-XGS-Chicago (SS2)](https://vecima.atlassian.net/wiki/spaces/PH/pages/137273176)
- 通用 Node Debug：[5.2 Node Debug Methods](https://vecima.atlassian.net/wiki/spaces/TS/pages/169182158)
- Coredump 分析：配合 `xpon-core-dump-debug` skill

---

## 1. Lab 环境速查（Chicago SS2）

| 设备 | IP / 访问 | 账号 | 备注 |
|------|-----------|------|------|
| **OLT Node (EXS1610)** | `10.254.20.137` (ma0) | `root` / **空密码** | SN `S220Z31018422`，device name `chicago` |
| Remote PC (console) | `10.254.20.184` | `root` / `vecima` | serial: `/dev/Node27` |
| EXC Chicago M OAM | `10.254.21.42` | CLI: `eacadmin/eacadmin` | NETCONF 控制器 |
| vPONMgr | `10.254.21.43` | WebUI: `admin@vecima.com` / `Vecima@1234` | 改 log level、OMCI trace |
| APPS Chicago | `10.254.21.44` | `root` / `nokia@` | |

**VLAN：**
- Node DHCP: 991 | vCM: 955 | CPE traffic: 1410

**Chicago 常用 PON / ONU（wiki 配置）：**

| ONU | PON | SN | pon_ni (XGS) |
|-----|-----|-----|--------------|
| ONU1 | PON1 | ZYXE53725310 | 0 |
| ONU2 | PON1 | ZYXE537252FE | 0 |
| ONU5 | PON1 | HTSZ39003930 | 0 |
| ONU3 | PON16 | HTSZ260D9008 | 30 |
| ONU4 | PON16 | SCOMA120044C | 30 |

**pon_ni 映射（BAL）：**
- `pon_ni = (物理PON口 - 1) × 2` → XGS 口（偶数）
- 例：PON1 → 0/1 (XGS/GPON)，PON16 → 30/31

**channeltermination 命名（log 中常见）：**
- 物理 PON16 → `pon.16`（YANG 名）→ `pon_ni=30`（BAL XGS）

---

## 2. 登录 Node

### 2.1 SSH（首选）

```bash
ssh root@10.254.20.137
# 密码为空，直接回车
```

登录后 prompt 类似：`root@xgs1610:~ [A]#`（`[A]`/`[B]` 为 RAUC 分区）

### 2.2 经 Remote PC 串口

```bash
ssh root@10.254.20.184    # 密码 vecima
minicom -w -D /dev/Node27
```

### 2.3 快速健康检查（登录后第一件事）

```bash
cat /etc/os-release
partition-helper.py info
systemctl is-active netconf-polt netopeer2 protocol-handler lag dev_mgmt_daemon redis
uptime
```

---

## 3. Debug 工具选型（决策树）

```
要查什么？
├─ 应用层状态（v-ani、forwarder、DHCP session、MAC 表）
│   └─ dbc <app>                    ← 首选，Vecima 应用 DbgCli
├─ netconf-polt 内置 Broadcom CLI（BAL API 层、OMCI 内部命令）
│   └─ /opt/bcm68620/daemon_attach -global netconf
│       ⚠ 与 dbc netconf 互斥，二选一
├─ BAL 硬件层（PON 状态、GEM、flow、ONU stats）
│   ├─ dump-stats.py                ← 快捷脚本，推荐
│   └─ echo "..." | /opt/bcm68620/example_user_appl   ← 一次性命令
└─ dev_mgmt_daemon（BAL 核心 daemon CLI）
    └─ /opt/bcm68620/daemon_attach -global dev_mgmt_daemon
```

| 工具 | 路径 | 作用域 | 典型场景 |
|------|------|--------|----------|
| **dbc** | `/usr/bin/dbc` | Vecima 应用 DbgCli | xpon 对象、PH DHCP、LAG 统计 |
| **daemon_attach** | `/opt/bcm68620/daemon_attach` | BCM daemon FIFO CLI | netconf 内部 CLI、dev_mgmt |
| **example_user_appl** | `/opt/bcm68620/example_user_appl` | BAL 交互 shell / 管道 | PON/GEM/flow 底层查询 |
| **dump-stats.py** | `/usr/bin/dump-stats.py` | BAL 统计封装 | 快速 dump pon/onu/gem/flow |

---

## 4. DBC（Debug Client）

### 4.1 基本用法

```bash
dbc <app>                    # 交互模式
dbc -A <app>                 # 同上
dbc -C "<cmd>" -A <app>      # 单条命令执行后退出
# Ctrl+D 退出
# 进入后输入 help 查看该 app 全部命令
```

### 4.2 可用 app 名

| dbc 命令 | 服务 | 常用 debug |
|----------|------|------------|
| `dbc netconf` | netconf-polt | `xpon get vani all`, `l2_mac_table get` |
| `dbc ph` | protocol-handler | `showFwdInfo all`, `dumpDHCPSes`, `showAntiSpoofing all` |
| `dbc lag` | lag | `nni get <0..3>`, `inni get all`, `lag get 1` |
| `dbc node-mgr` | node-mgr | `serial`, `mac`, `get temp`, `get qsfp` |
| `dbc swm` | swmgr | `info`（双分区软件信息） |
| `dbc led-mgr` | led-mgr | `alarm_record` |
| `dbc metrics-mgr` | metrics-mgr | metrics 相关 |
| `dbc sysmon` | sysmon | CPU/内存/磁盘 |
| `dbc hwmon` | hwmon | 硬件监控 |
| `dbc notif` | notif-mgr | 通知 |
| `dbc lldp-ctlr` | lldp-ctlr | LLDP |

App 名定义见 `xpon-libs/debug/include/dbg.h` → `gAppList[]`。

### 4.3 netconf DBC 常用命令

```bash
dbc netconf
help
xpon get vani all
xpon get channeltermination all
xpon get onus_onu all
l2_mac_table get
l2_mac_table dump
```

`xpon get <type> <name|all>` 支持的 type：
`channelgroup|channelpair|channelpartition|channeltermination|wavelen_prof|hardware|ani|vani|ani_v-enet|enet|pots|gem|tcont|td_prof|classifier|policy|policy_profile|forwarder|onus_onu|...`

Handler 实现：`netconf-polt/netconf_server/modules/bbf-xpon/bbf-debug.c`

### 4.4 PH DBC 常用命令

```bash
dbc ph
showDhcpv4Profile
showVlanSubItfCfg
showFwdInfo all
dumpDHCPSes
dumpDHCPV6Ses
showAntiSpoofing all
showDsFlooding all DHCPv4
pktCapture enable <filename> <count>   # DHCPv6 抓包
pktCapture disable
```

Handler 实现：`xpon-apps/protocol-handler/common/src/ph_dbg.c`

### 4.5 LAG / INNI 统计

```bash
dbc lag
nni get 0              # uplink port 0..3
inni get all           # PON internal switch port
lag get 1
```

**PON ↔ INNI 映射：**

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

附着到后台 BCM daemon 的 CLI FIFO，用于 netconf-polt 或 dev_mgmt_daemon 的内置 CLI。

### 5.1 用法

```bash
/opt/bcm68620/daemon_attach [-global] [-no-lineedit] [-path path] <daemon_name>
```

| 参数 | 含义 |
|------|------|
| `-global` | 全机唯一 daemon 实例（**生产 node 必须加**） |
| `-no-lineedit` | 禁用行编辑（脚本/pipe 场景） |
| `-path path` | FIFO 路径，默认 `/tmp` |

### 5.2 常用 daemon 名

```bash
# netconf-polt 内置 CLI（BAL host API、OMCI 等）
/opt/bcm68620/daemon_attach -global netconf

# BAL 核心 daemon
/opt/bcm68620/daemon_attach -global dev_mgmt_daemon
```

实现：`netconf-polt/daemon/attach/bcmolt_daemon_attach.c`

### 5.3 与 dbc 互斥

`dbc netconf` 连接期间，`daemon_attach netconf` 会被阻塞并提示：

> `dbc is active. Please exit dbc firstly if use daemon_attach!`

**规则：先 Ctrl+D 退出 dbc，再 daemon_attach。**

源码：`netconf-polt/netconf_server/bcmolt_netconf_server.c` → `DaemonCliThread()`

### 5.4 dbc vs daemon_attach 对比

| | dbc netconf | daemon_attach netconf |
|--|-------------|----------------------|
| 接口 | Vecima DbgCli（xpon get, l2_mac_table） | Broadcom bcmcli（/a/g, /api/...） |
| 适用 | YANG 对象、业务 debug | BAL API 原始命令、脚本化 CLI |
| 互斥 | 与 daemon_attach 互斥 | 与 dbc netconf 互斥 |

---

## 6. BAL：example_user_appl

BAL 交互入口，位于 `/opt/bcm68620/example_user_appl`。

**问题：** 交互模式下内部 log 刷屏，输出难读。

**推荐：** 用 `echo` 管道一次性执行：

```bash
# PON1 (pon_ni=0) 状态
echo "/a/g object=pon_interface pon_ni=0 state" | /opt/bcm68620/example_user_appl

# PON1 active ONU 数量
echo "/a/g object=pon_interface pon_ni=0 number_of_active_onus" | /opt/bcm68620/example_user_appl

# PON16 (pon_ni=30)
echo "/a/g object=pon_interface pon_ni=30 state" | /opt/bcm68620/example_user_appl

# ONU 状态（PON1, onu_id=0）
echo "/a/g object=onu pon_ni=0 onu_id=0" | /opt/bcm68620/example_user_appl

# GEM 列表
echo "/a/m max_msgs=20 filter_invert=no object=itupon_gem pon_ni=0" | /opt/bcm68620/example_user_appl

# Flow 列表
echo "/a/m max_msgs=50 filter_invert=yes object=flow" | /opt/bcm68620/example_user_appl

# PON 统计（不清 counter）
echo "/a/t clear=no object=pon_interface sub=itu_pon_stats pon_ni=0" | /opt/bcm68620/example_user_appl

# 上联 NNI 统计
echo "/a/t clear=no object=nni_interface sub=stats id=0" | /opt/bcm68620/example_user_appl
```

也可直接进入交互 shell（调试完 `quit` 退出）：

```bash
cd /opt/bcm68620 && ./example_user_appl
```

---

## 7. dump-stats.py（BAL 统计快捷方式）

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

Chicago 常用：`dump-stats.py pon pon1` / `dump-stats.py onu pon16`。

---

## 8. Log 收集与分析

### 8.1 日志位置

```bash
# 统一 syslog（首选）
cat /run/log/messages
tail -F /run/log/messages
tail -500 /run/log/messages | grep -iE 'error|fail|segfault|critical|warn'

# systemd journal
journalctl --no-pager -n 200
journalctl -f
journalctl -p err..alert --since "1 hour ago" --no-pager
```

### 8.2 按服务过滤

```bash
journalctl -u netconf-polt -b --no-pager | tail -100
journalctl -f -u netconf-polt
journalctl -f -u protocol-handler
journalctl -f -u lag
journalctl -f -u netopeer2
journalctl -f -u dev_mgmt_daemon
```

### 8.3 关键 systemd unit

| Unit | 作用 |
|------|------|
| `netconf-polt` | NETCONF/YANG、PON/ONU、OMCI |
| `protocol-handler` | DHCP/PPPoE/转发控制 |
| `lag` | 上联 NNI/LAG |
| `netopeer2` | NETCONF SSH 服务端 |
| `dev_mgmt_daemon` | BAL 核心 daemon |
| `logsvr` | 集中日志接收 |
| `redis` | 内部 KV（DHCP session 等） |
| `metrics-mgr` | 性能指标 |
| `event-monitor` | 事件分发 |

### 8.4 调整 log level

**vPONMgr：** Setting → Service Groups → OLT Logging Configuration
（或 OLT Inventory → Configuration → Logging）

Chicago wiki 常用 debug 源：
- `omci-me-layer`, `omci-transport`, `omci-svc`, `netconf`, `bal-api` → debug

### 8.5 OMCI log 抓取

```bash
# 1. vPONMgr 设 OMCI ME Layer / Service / Transport 为 Debug
# 2. node 上：
journalctl --no-pager > /tmp/omci.log

# 过滤 OMCI 帧（全 ONU）
grep "omci_stack_rx\.c.*{olt_id=.*pon_if=.*onu_id=.*cookie=.*}: " /tmp/omci.log \
  | sed 's/^.*{.*}: //g' > /tmp/omci.pcap

# 指定 ONU（例：pon_if=2, onu_id=55）
grep "omci_stack_rx\.c.*{olt_id=.*pon_if=.*onu_id=.*cookie=.*}: " /tmp/omci.log \
  | sed 's/^.*{olt_id=0 pon_if=2, onu_id=55.*}: //g' > /tmp/omci.pcap
```

Wireshark 分析：导入 omci.pcap（No dummy header），插件见 [omci-wireshark-dissector](https://github.com/0liv1er/omci-wireshark-dissector)。

### 8.6 PLOAM log 抓取

```bash
# 清 log（device_id=0 对应 pon_ni 0~15）
echo "/a/o object=log_file sub=clear device_id=0 file_id=ddr" | /opt/bcm68620/example_user_appl

# 设 debug level
echo "/a/s object=log device_id=0 name=ploam_us0 level={print=debug save=debug }" | /opt/bcm68620/example_user_appl
echo "/a/s object=log device_id=0 name=ploam_ds0 level={print=debug save=debug }" | /opt/bcm68620/example_user_appl

# dump
echo "user/read_embedded_logger device=0 file_id=ddr" | /opt/bcm68620/example_user_appl > /tmp/ploam.log

# 恢复 info
echo "/a/s object=log device_id=0 name=ploam_us0 level={print=info save=info }" | /opt/bcm68620/example_user_appl
echo "/a/s object=log device_id=0 name=ploam_ds0 level={print=info save=info }" | /opt/bcm68620/example_user_appl

# 分析
grep message_id /tmp/ploam.log
```

### 8.7 Support info 归档

```bash
ls /tmp/debug/support-info-logs*.tar.gz
# coredump 解密分析 → 见 xpon-core-dump-debug skill
```

### 8.8 拔插光纤 / indication 测试 log 抓取

Agent 或人工配合测试时，在 node 上后台抓 `netconf-polt` journal，测试后拉回开发机分析。

**在 node 上启动抓取：**

```bash
CAP=/tmp/fiber_test_capture.log
date "+%Y-%m-%d %H:%M:%S" > /tmp/fiber_test_start.txt
echo "=== START $(cat /tmp/fiber_test_start.txt) ===" >> "$CAP"
nohup journalctl -f -u netconf-polt -o short-precise >> "$CAP" 2>&1 &
echo $! > /tmp/fiber_test_jpid
```

**测试完成后停止并拉回（开发机，需 sshpass）：**

```bash
sshpass -p '' ssh root@10.254.20.137 'kill $(cat /tmp/fiber_test_jpid) 2>/dev/null'
sshpass -p '' scp root@10.254.20.137:/tmp/fiber_test_capture.log ./fiber_test.log
sshpass -p '' scp root@10.254.20.137:/tmp/fiber_test_start.txt ./marker.txt
```

**分析关键字（拔插光纤）：**

```bash
grep -iE "pon_interface LOS|LOS status|indication '|deactivation|activation|ranging|online_onus|notif_mgr|alarm_id" fiber_test.log \
  | grep -v "ONU_discovered: onu_id=65535"
```

---

## 9. NETCONF / Sysrepo（配置侧 debug）

```bash
# 本地 NETCONF client
netopeer2-cli
> connect --port 830 --host 127.0.0.1 --login root

# 直接读 datastore
sysrepocfg -d running -X
sysrepocfg -d operational -X
sysrepocfg -d running -m bbf-xpon -X

# 软件/分区
partition-helper.py info
rauc status --detailed
```

---

## 10. 常见排查流程

### 10.1 ONU 不上线

```bash
systemctl status netconf-polt dev_mgmt_daemon --no-pager
echo "/a/g object=pon_interface pon_ni=0 state" | /opt/bcm68620/example_user_appl
dump-stats.py pon pon1
dbc -C "xpon get vani all" -A netconf
journalctl -u netconf-polt --since "10 min ago" --no-pager | grep -i omci
```

### 10.2 DHCP 不通

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

### 10.4 替换 Binary（开发迭代）

EXS1610 默认 `usr.mount` 将 `/usr` 只读挂载（RAUC rootfs overlay）。**直接 scp 到 `/usr/bin/` 会失败**；须先 disable `usr.mount` 并 reboot，重启后 `/usr` 才可写。

#### 流程（在 node 上操作）

```bash
# 1. 登录 node
ssh root@10.254.20.137

# 2. 禁用 usr.mount（使下次启动 /usr 可写）
systemctl disable usr.mount

# 3. 重启（必须；disable 后须 reboot 才生效）
reboot
```

#### reboot 完成后（在开发机上 scp）

```bash
# 4. 等待 node 起来后，再 scp（reboot 前不要 scp）
sshpass -p '' scp <path>/bcmolt_netconf_server root@10.254.20.137:/usr/bin/bcmolt_netconf_server

# 5. 重启服务并验证
sshpass -p '' ssh root@10.254.20.137 \
  "chmod 755 /usr/bin/bcmolt_netconf_server && systemctl restart netconf-polt.service && systemctl status netconf-polt.service --no-pager"
sshpass -p '' ssh root@10.254.20.137 "dbc -C help -A netconf"   # 应打印 Usage，不应 SIGSEGV
```

#### 本机产物路径

```bash
cd ~/works/repo && . setup-env
bitbake netconf-polt -c compile -f
find ~/works/repo/build-xpon/tmp/work -path '*netconf-polt*' -name bcmolt_netconf_server
```

#### 注意

| 步骤 | 说明 |
|------|------|
| `systemctl disable usr.mount` | **必须先做**，否则 `/usr` 只读 |
| `reboot` | disable 后**必须 reboot**，scp 才有意义 |
| scp 时机 | **reboot 完成后**再 scp，不要在 disable 后、reboot 前 scp |
| 整包升级 | 生产/正式验证用 RAUC bundle，不走此 dev 流程 |
| scp 工具 | 开发机用 `sshpass -p '' scp ...`（见 §11.2） |

### 10.5 拔插光纤 — 触发的 indication（Chicago PON16 实测）

物理 PON16（`pon_ni=30`，`pon.16`），2 个 ONU 在线时拔插一次光纤的典型序列。

**拔光纤（LOS ON）：**

| 顺序 | Indication / 事件 | 模块 |
|------|-------------------|------|
| 1 | `pon_interface LOS` status=ON | `bbf-xpon.c` `_pon_interface_indication_cb` |
| 2 | PON LOS alarm 上报（alarm_id=50, `is_clear:false`） | `ipc-notif-mgr.c` |
| 3 | `pon_interface LOS status is on` | `bbf-xpon.c` |
| 4 | ONU audit debounce cleared | `bbf-xpon-v-ani.c` |
| 5 | `onu_deactivation_completed`（每个在线 ONU） | `bbf-xpon-v-ani.c` |
| 6 | 从 `online_onus` 删除 + v-ani → `onu-not-present-with-v-ani` | `bbf-xpon-channel-termination.c` |
| 7 | `ipc_notif_mgr_send_onu_presence` | `ipc-notif-mgr.c` |
| 8 | OMCI deactivate + `_onualarm_clearall` (reason=LOS) | `omci_svc` / `bbf-xpon-v-ani.c` |

**插回光纤（恢复）：**

| 顺序 | Indication / 事件 | 备注 |
|------|-------------------|------|
| 1 | `pon_interface LOS` status=OFF | 可能因 `online_onus` 为空被 skip：`LOS OFF is not reasonable` |
| 2 | `ONU_discovered` | 每个 ONU 一次 |
| 3 | `ranging_completed` | |
| 4 | `onu_activation_completed` | |
| 5 | OMCI activate 启动 | |
| 6 | `onu-present` presence 通知可能被 skip | flap 保护 |
| 7 | OMCI UNI link-down alarm (id=41) 后 clear | 以太口状态，非 PON LOS |

**~10s 后（LOS WA 定时器）：**

| 事件 | 说明 |
|------|------|
| `_cterm_pon_los_check_timeout_handler` | BAL LOS-OFF 行为不一致时的 workaround，清除 PON LOS alarm (`is_clear:true`) |

**本次未触发的 indication：** 逐 ONU XGPON PHY alarm（`looci`/`dowi`/`dgi` 等）— LOS 路径直接 bulk deactivate，未走单 ONU PHY alarm 分支。

源码锚点：
- PON LOS：`netconf-polt/netconf_server/modules/bbf-xpon/bbf-xpon.c` → `BCMOLT_PON_INTERFACE_AUTO_SUBGROUP_LOS`
- LOS WA 定时器：`bbf-xpon-channel-termination.c` → `_cterm_pon_los_check_timeout_handler`（10s）
- ONU indication：`bbf-xpon-v-ani.c` → `_onu_indication_cb`

---

## 11. Agent / 本地 PC 远程 SSH

Chicago OLT：`root@10.254.20.137`，**空密码**。

### 11.1 手动 SSH（终端）

```bash
ssh root@10.254.20.137    # 密码提示时直接回车
```

### 11.2 sshpass（Agent / 脚本自动 SSH）

**安装位置：本地 PC / LXD 开发容器**（不是 OLT）。`sshpass` 是 SSH **客户端**工具，在发起连接的一侧安装。

Vecima LXD 容器（vcmos 5.0）的 dnf 仓库**不含** `sshpass` 包，需从源码编译：

```bash
# 在 LXD 容器内（已有 gcc/make/curl）
cd /tmp
curl -fsSL -o sshpass-1.10.tar.gz \
  https://downloads.sourceforge.net/project/sshpass/sshpass/1.10/sshpass-1.10.tar.gz
tar xzf sshpass-1.10.tar.gz && cd sshpass-1.10
./configure --prefix=$HOME/.local && make -j$(nproc) && make install

# 验证
sshpass -V
sshpass -p '' ssh -o StrictHostKeyChecking=no root@10.254.20.137 'hostname'
```

安装路径：`~/.local/bin/sshpass`（oreo 用户 PATH 已包含 `~/.local/bin`）。

**Ubuntu LXD 宿主机**可直接：`sudo apt install sshpass`

### 11.3 Agent 自动连 OLT 示例

```bash
sshpass -p '' ssh root@10.254.20.137 'journalctl -u netconf-polt -n 50 --no-pager'
sshpass -p '' scp root@10.254.20.137:/run/log/messages /tmp/olt-messages.log
```

### 11.4 备选：SSH 公钥免密

将本机 `~/.ssh/id_ed25519.pub` 写入 OLT `/root/.ssh/authorized_keys`，之后无需 sshpass。

### 11.5 Agent 远程操作前提

- `~/.local/bin/sshpass` 已安装并验证（§11.2）→ Agent 可自动 SSH/scp 到 Chicago OLT
- 未安装时：用户终端手动 SSH，或粘贴 log / scp 文件给 Agent 分析

---

## 12. 硬件 / 制造信息

```bash
onie-syseeprom
cat /run/dev/rip/serial-num
cat /run/dev/rip/mac-base
sensors
dbc -C "get hwmonall" -A node-mgr
```

---

## Quick Reference Card

```bash
# 登录
ssh root@10.254.20.137          # 空密码

# 健康
systemctl is-active netconf-polt protocol-handler lag dev_mgmt_daemon
cat /etc/os-release

# 应用 debug
dbc netconf                     # xpon get vani all
dbc ph                          # dumpDHCPSes
dbc lag                         # inni get all

# BAL debug
dump-stats.py pon pon1
echo "/a/g object=pon_interface pon_ni=0 state" | /opt/bcm68620/example_user_appl

# netconf 内置 CLI（先退出 dbc netconf）
/opt/bcm68620/daemon_attach -global netconf

# Log
tail -F /run/log/messages
journalctl -f -u netconf-polt
journalctl -p err..alert --since "1 hour ago" --no-pager

# 替换 binary（须先 disable usr.mount + reboot，再 scp）
sshpass -p '' ssh root@10.254.20.137 "systemctl disable usr.mount && reboot"
# 等 node 起来后：
sshpass -p '' scp <path>/bcmolt_netconf_server root@10.254.20.137:/usr/bin/
sshpass -p '' ssh root@10.254.20.137 "chmod 755 /usr/bin/bcmolt_netconf_server && systemctl restart netconf-polt"

# 拔插光纤 log 抓取（见 §8.8 / §10.5）
```
