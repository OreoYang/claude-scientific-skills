---
name: xpon-core-dump-debug
description: This skill should be used when the user needs to "debug core dump", "analyze xpon crash", "debug bcmolt_netconf_server", "analyze segmentation fault", or needs guidance on GDB core dump analysis for embedded Linux systems.
version: 1.3.1
---

# xpon Core Dump Debug Skill

Complete workflow for debugging core dumps from bcmolt_netconf_server and xpon-related embedded Linux applications.

## Quick Start

### Unpacked Core Dump

```bash
# Set these to paths inside the workspace, not /tmp (see "Extract Debug Symbols" below)
DBGROOT=$(pwd)/dbgroot
CORE=<path-to-core-file>

/usr/bin/gdb --nh --nx -q -batch \
  -ex "set debuginfod enabled off" \
  -ex "set auto-load safe-path /" \
  -ex "set sysroot $DBGROOT" \
  -ex "file $DBGROOT/usr/bin/bcmolt_netconf_server" \
  -ex "core $CORE" \
  -ex "thread 1" \
  -ex "bt 40"
```

### Support-Info-Logs Archive

```bash
# Extract and decrypt (requires /decrypt_keys/dorado_private.pem)
# IMPORTANT: use the workspace/current working directory, NOT /tmp.
# /tmp is wiped on reboot; placing artifacts in the workspace keeps them
# persistent and lets the user inspect them directly in the IDE.
WORKDIR=$(pwd)/support-debug
mkdir -p "$WORKDIR" && cd "$WORKDIR"
tar zxf <archive>.tar.gz
cd debugdump && entra_rpd_decrypt encrypted.tar.gz.enc
tar zxf encrypted.tar.gz
cd encrypted/CoreDump/coredump/
unzstd --rm *.zst
CORE=$(ls core.* | head -1)

# Analyze
gdb -ex "set sysroot $DBGROOT" -ex "core $CORE"
```

## Environment Setup

### Required Tools

| Tool | Purpose |
|------|---------|
| `gdb` | GNU Debugger |
| `entra_rpd_decrypt` | Decrypt encrypted archives (uses `/decrypt_keys/dorado_private.pem`) |
| `unzstd` | Decompress .zst files |

### Required Files

| File | Purpose |
|------|---------|
| `*.dbg.tar.bz2` | Debug symbols package |
| `*.raucb` | RAUC bundle with rootfs |
| `support-info-logs-*.tar.gz` | Encrypted core dump archive |

### Extract Debug Symbols

```bash
# IMPORTANT: place DBGROOT inside the workspace/current working directory,
# NOT under /tmp. This keeps the rootfs and debug symbols persistent across
# reboots and lets the user browse them directly in the IDE.
DBGROOT=$(pwd)/dbgroot
mkdir -p "$DBGROOT"

# Extract debug symbols
tar -xjf *.dbg.tar.bz2 -C "$DBGROOT"

# Extract RAUC bundle rootfs
mkdir -p "$DBGROOT/rauc_temp"
unsquashfs -f -d "$DBGROOT/rauc_temp" *.raucb
tar -xjf "$DBGROOT/rauc_temp"/*.rootfs.tar.bz2 -C "$DBGROOT"
rm -rf "$DBGROOT/rauc_temp"

# Verify both stripped and unstripped exist
file $DBGROOT/usr/bin/bcmolt_netconf_server       # stripped
file $DBGROOT/usr/bin/.debug/bcmolt_netconf_server # with debug_info
```

**Critical**: Both stripped and unstripped versions must exist for symbol loading.

## Common Core Types

| Pattern | Service |
|---------|---------|
| `core.bcmolt_netconf.*` | NETCONF server |
| `core.lag.*` | LAG daemon |
| `core.bcmoni*.*` | BCMMONI daemon |
| `core.bcmolt*.*` | BCMOLT services |

## GDB Commands

| Command | Purpose |
|---------|---------|
| `bt [n]` | Backtrace |
| `thread N` | Switch thread |
| `frame N` | Switch frame |
| `info threads` | List threads |
| `info sharedlibrary` | Symbol status |
| `info locals` | Local variables |
| `info args` | Function arguments |
| `p var` | Print variable |
| `x/ngx addr` | Examine memory |

## Analysis Workflow

1. **Get backtrace**: `bt 40`
2. **Switch to crash frame**: `frame 1`
3. **Examine variables**: `info args`, `info locals`
4. **Check symbols**: `info sharedlibrary`

## Common Issues

| Issue | Solution |
|-------|----------|
| Could not load symbols | Verify `.debug/` subdirectory has unstripped files |
| ? in backtrace | Check BuildID: `readelf -n file \| grep BuildID` |
| entra_rpd_decrypt not found | Check `/usr/local/bin/entra_rpd_decrypt` |
| Cannot access memory | Use-after-free or invalid pointer |

## ONU/OMCI Crash Patterns

| Pattern | Function | Issue |
|---------|----------|-------|
| `onu_context->XXX` | omci_svc_state_* | Context freed during async operation |
| `onu_cfg->XXX` | omci_svc_onu_* | NULL after ONU deactivation |
| Race condition | State machine callbacks | Concurrent activation/deactivation |

### Use-After-Free Detection

```bash
# Check pointer validity
p <ptr>
x/10gx <ptr>

# Check all threads for race
thread apply all bt

# Find ONU source files
find $DBGROOT/usr/src/debug -path "*/libomcisvc/*.c"
```

### Key Indicators

- Pointer address looks "odd" (e.g., ends in small hex like 0x3e8)
- Cannot access memory at address
- Crash in state machine callback with async callstack
- Multiple threads manipulating ONU state

## Case Studies Reference

### dbg_xpon_handler SIGSEGV
- **Location**: `bbf-debug.c:235`
- **Cause**: `argv[0]` was NULL, not checked before `strcmp()`
- **Fix**: Add null check: `if (argc < 1 \|\| !argv[0])`

### omci_svc_state_up_sequence_end_event_start SIGSEGV
- **Location**: `omci_svc_onu.c:3587`
- **Cause**: Use-after-free of `onu_context` during async callback
- **Pattern**: ONU activation completes while deactivation in progress

## Pre-Flight Checklist

- [ ] DBGROOT and support-debug are under the **workspace directory**, not `/tmp` (persistent + user-accessible)
- [ ] Core file exists and readable
- [ ] DBGROOT has complete filesystem
- [ ] Debug symbols in `.debug/` subdirectories
- [ ] Stripped files in normal directories
- [ ] `set sysroot` points to DBGROOT
- [ ] `info sharedlibrary` shows "Yes" for main libraries

## Analysis Report Template

Use this template for final coredump analysis reports:

```markdown
# Coredump Analysis Report

## Summary
<one-paragraph description of crash including process, location, and root cause>

## Environment
| Item | Value |
|------|-------|
| Build | <build version> |
| Platform | <hardware/platform> |
| PID | <process id> |
| Crash thread | <thread id> |
| Crash time | <timestamp UTC> |
| Signal | <signal description> |
| Fault address | <memory address> |

## Complete Backtrace
```
#0  <function> (<args>)
     at <source>:<line>
#1  <function> (<args>)
     at <source>:<line>
...
```

## Root Cause

### Crash Location
<source>:<line> — description of code

```c
// <source>:<line>
<problematic code>
```

### Why the Pointer is Invalid
<explanation of memory corruption, use-after-free, or invalid pointer>

### Race Condition Trigger (if applicable)
<step-by-step sequence of events leading to crash>

### Call Chain Summary
<summary of call stack with key functions>

## Fix Applied

**File**: <source file>

<description of fix with diff if applicable>

```c
// Before/After comparison
```

## Reproduction Conditions
<conditions required to reproduce the crash>

## Severity / Impact
<service impact and affected components>
```

### Example Report Key Elements

| Section | Content |
|---------|---------|
| Summary | Process, crash location, root cause (1 paragraph) |
| Environment | Build, platform, PID, thread, time, signal, fault address |
| Backtrace | Full call stack with source/line info |
| Root Cause | Crash location, pointer analysis, race condition, call chain |
| Fix | File changed, diff, explanation |
| Reproduction | Specific conditions to trigger crash |
| Severity | Service impact, affected components |
