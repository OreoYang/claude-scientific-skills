# Reference: GDB, Core Types, ONU Patterns

## GDB Commands

| Command | Purpose |
|---------|---------|
| `bt [n]` | Backtrace (n frames) |
| `thread N` | Switch thread |
| `frame N` | Switch stack frame |
| `info threads` | List all threads |
| `info sharedlibrary` | Symbol load status per library |
| `info locals` | Local variables in current frame |
| `info args` | Function arguments in current frame |
| `p var` | Print variable |
| `x/ngx addr` | Examine memory (n units, format x, address) |
| `thread apply all bt` | Backtrace every thread (race / UAF) |

### Standard GDB Init (batch)

```gdb
set debuginfod enabled off
set auto-load safe-path /
set sysroot <DBGROOT>
file <DBGROOT>/<binary>
core <core-file>
thread 1
bt 40
```

## Core Filename → Service

| Pattern | Service | Default binary under DBGROOT |
|---------|---------|-------------------------------|
| `core.bcmolt_netconf.*` | NETCONF server | `usr/bin/bcmolt_netconf_server` |
| `core.lag.*` | LAG daemon | `usr/bin/lag` |
| `core.bcmoni*.*` | BCMMONI | `usr/bin/bcmoni` |
| `core.bcmolt*.*` | BCMOLT services | `usr/bin/bcmolt_netconf_server` |
| `core.protocol*.*` | protocol-handler | `usr/bin/protocol-handler` |

Override with `gdb_bt.sh --binary` when auto-detection is wrong.

## Analysis Workflow

1. **Backtrace**: `bt 40`
2. **Crash frame**: `frame 1` (or frame shown in SIGSEGV line)
3. **Variables**: `info args`, `info locals`
4. **Symbols**: `info sharedlibrary` — main libs should show **Yes**
5. **BuildID** (if `?` in backtrace):

```bash
readelf -n "$DBGROOT/usr/bin/bcmolt_netconf_server" | grep -i buildid
readelf -n "$CORE" | grep -i buildid
```

## support-info-logs Decrypt Troubleshooting

| Issue | Solution |
|-------|----------|
| `entra_rpd_decrypt not found` | Install tool; check `/usr/local/bin/entra_rpd_decrypt` |
| `Missing argument for option: d` | Drop `-d` / `-ed` flags; run `entra_rpd_decrypt encrypted.tar.gz.enc` from `debugdump/` |
| Decrypt fails / no `encrypted.tar.gz` | Confirm `/decrypt_keys/dorado_private.pem` exists and is readable |
| Used `ENC_AES_KEY` as key | Wrong key type — host tool uses RSA key at `/decrypt_keys/dorado_private.pem` automatically |
| `No core.* files found` | Archive may have no crash (`encrypted/CoreDump/list.txt` → "There are no coredumps"); logs in `encrypted/` are still valid |
| Core is `*.zst` | Run `unzstd --rm encrypted/CoreDump/coredump/*.zst` after tar extract |

## Common Issues

| Issue | Solution |
|-------|----------|
| Could not load symbols | Check `usr/bin/.debug/` has unstripped binary with `debug_info` |
| `?` in backtrace | BuildID mismatch — use matching `*.dbg.tar.bz2` + `*.raucb` |
| Cannot access memory | Likely use-after-free or corrupt pointer |
| Wrong binary / no threads | Re-run `detect_binary.sh`; verify core is complete |

## ONU / OMCI Crash Patterns

| Pattern | Function family | Typical issue |
|---------|-----------------|---------------|
| `onu_context->XXX` | `omci_svc_state_*` | Context freed during async callback |
| `onu_cfg->XXX` | `omci_svc_onu_*` | NULL after ONU deactivation |
| State machine in stack | OMCI FSM callbacks | Concurrent activate/deactivate race |

### Use-After-Free Checks

```gdb
p <ptr>
x/10gx <ptr>
thread apply all bt
```

Find ONU sources in DBGROOT:

```bash
find "$DBGROOT/usr/src/debug" -path "*/libomcisvc/*.c" 2>/dev/null
```

### Key Indicators

- Pointer address looks "odd" (e.g. ends in `0x3e8`)
- GDB: "Cannot access memory at address"
- Crash in async/state-machine callback
- Multiple threads touching ONU state in `thread apply all bt`

## Case Studies

### dbg_xpon_handler SIGSEGV

- **Location**: `bbf-debug.c:235`
- **Cause**: `argv[0]` NULL, used in `strcmp()` without check
- **Fix**: `if (argc < 1 || !argv[0])` guard before strcmp

### omci_svc_state_up_sequence_end_event_start SIGSEGV

- **Location**: `omci_svc_onu.c:3587`
- **Cause**: Use-after-free of `onu_context` in async callback
- **Pattern**: ONU activation completes while deactivation still in progress

## Pre-Flight Checklist

- [ ] `DBGROOT` and `support-debug` under workspace, not `/tmp`
- [ ] Core file exists and is readable
- [ ] DBGROOT has complete rootfs layout
- [ ] `.debug/` subdirs contain unstripped binaries
- [ ] Stripped binaries in normal `usr/bin`, `usr/lib`
- [ ] `verify_dbgroot.sh` passes
- [ ] `info sharedlibrary` shows **Yes** for main libraries

## Analysis Report Template

See [examples/sample-report.md](examples/sample-report.md) for a filled example.

Required sections:

1. **Summary** — process, location, root cause (one paragraph)
2. **Environment** — build, platform, PID, thread, time, signal, fault address
3. **Complete Backtrace**
4. **Root Cause** — crash location, pointer analysis, race trigger if any
5. **Fix Applied** — file, before/after
6. **Reproduction Conditions**
7. **Severity / Impact**
