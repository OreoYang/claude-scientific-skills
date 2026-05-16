---
name: xpon-core-dump-debug
description: This skill should be used when the user needs to "debug core dump", "analyze xpon crash", "debug bcmolt_netconf_server", "analyze segmentation fault", or needs guidance on GDB core dump analysis for embedded Linux systems.
version: 1.0.0
---

# xpon Core Dump Debug Skill

This skill provides complete workflow for debugging core dumps from bcmolt_netconf_server and xpon-related embedded Linux applications.

## Quick Start

```bash
DBGROOT=/home/oreo/gdb/20260514.014942
CORE=/home/oreo/gdb/core.bcmolt_netconf.unpacked

/usr/bin/gdb --nh --nx -q -batch \
  -ex "set debuginfod enabled off" \
  -ex "set auto-load safe-path /" \
  -ex "set sysroot $DBGROOT" \
  -ex "file $DBGROOT/usr/bin/bcmolt_netconf_server" \
  -ex "core $CORE" \
  -ex "thread 1" \
  -ex "bt 40"
```

## Environment Setup

### Required Files

| File | Purpose |
|------|---------|
| `core.bcmolt_netconf.unpacked` | Core dump file |
| `hank-olt-image-exs1610-1031.dbg.tar.bz2` | Debug symbols package |
| `hank-olt-bundle-exs1610-1031.raucb` | System image (RAUC bundle) |

### Extract Debug Symbols and Root Filesystem

```bash
#!/bin/bash
DBGROOT=/home/oreo/gdb/20260514.014942

# Extract debug symbols
tar -xjf /home/oreo/gdb/hank-olt-image-exs1610-1031.dbg.tar.bz2 -C "$DBGROOT"

# Extract RAUC bundle
mkdir -p "$DBGROOT/rauc_temp"
unsquashfs -f -d "$DBGROOT/rauc_temp" /home/oreo/gdb/hank-olt-bundle-exs1610-1031.raucb

# Extract root filesystem
tar -xjf "$DBGROOT/rauc_temp/xpon-olt-image-exs1610.rootfs.tar.bz2" -C "$DBGROOT"
rm -rf "$DBGROOT/rauc_temp"
```

### Verify File Structure

```bash
# Check that both stripped and unstripped files exist
file $DBGROOT/usr/bin/bcmolt_netconf_server
# Expected: ELF 64-bit LSB pie executable, ..., stripped

file $DBGROOT/usr/bin/.debug/bcmolt_netconf_server
# Expected: ELF 64-bit LSB pie executable, ..., with debug_info, not stripped
```

**Critical**: Both stripped (main file) and unstripped (.debug/ directory) versions must exist for GDB to load symbols correctly.

## GDB Commands Reference

### Essential Commands

| Command | Purpose |
|---------|---------|
| `bt [n]` | Show backtrace (n frames) |
| `thread N` | Switch to thread N |
| `frame N` | Switch to stack frame N |
| `info threads` | List all threads |
| `info sharedlibrary` | Show shared library symbol status |
| `info locals` | Show local variables |
| `info args` | Show function arguments |
| `list start,end` | Show source code lines |
| `p var` | Print variable value |
| `x/10s addr` | Examine memory as strings |
| `set sysroot path` | Set root filesystem path |

### Interactive Debugging Session

```bash
/usr/bin/gdb --nh --nx -q \
  -ex "set debuginfod enabled off" \
  -ex "set auto-load safe-path /" \
  -ex "set sysroot $DBGROOT" \
  -ex "file $DBGROOT/usr/bin/bcmolt_netconf_server" \
  -ex "core $CORE"
```

## Analysis Workflow

### Step 1: Identify Crash Location

```bash
# Get backtrace
bt 40

# Switch to crashing frame
frame 1

# Show source code
list
```

### Step 2: Examine Variables

```bash
# Check function arguments
info args

# Check local variables
info locals

# Print specific variable
p variable_name
```

### Step 3: Verify Symbol Loading

```bash
# Check which libraries have symbols loaded
info sharedlibrary

# Look for "Yes" (symbols loaded) vs "No" (symbols missing)
```

## Common Issues and Solutions

### "Could not load shared library symbols"

**Cause**: sysroot path incorrect or .debug structure mismatch

**Solution**: Verify stripped and unstripped files exist in correct locations:
- Main file: `$DBGROOT/usr/lib/libxxx.so.x.y.z`
- Debug file: `$DBGROOT/usr/lib/.debug/libxxx.so.x.y.z`

### "??" in Backtrace (Cannot Resolve Symbols)

**Cause**: Debug symbols not loaded or address mismatch

**Solution**:
1. Check BuildID matches: `readelf -n file | grep BuildID`
2. Verify .debug file exists
3. Ensure `set sysroot` points to correct DBGROOT

### "Can't open file during file-backed mapping note processing"

**Cause**: Runtime files (like /dev/shm) not in DBGROOT

**Solution**: Usually safe to ignore - these are transient runtime files that don't exist in the filesystem snapshot

## Recent Crash Analysis (Reference)

### Crash: dbg_xpon_handler SIGSEGV

**Location**: `bbf-debug.c:235`

**Backtrace**:
```
#0  __strcmp_sse2_unaligned ()
#1  dbg_xpon_handler (argc=0, argv=0x7fb618015690) at bbf-debug.c:235
#2  ExecuteLine (line="xpon") at dbgCli.c:382
```

**Root Cause**:
```c
static int dbg_xpon_handler(int argc, char *argv[])
{
    char *action = argv[0];  // argc=0, argv[0]=NULL!
    if (strcmp(action, "get") == 0)  // CRASH: strcmp(NULL, "get")
```

**Values**:
- `argc = 0`
- `argv[0] = NULL` (not checked)

**Fix**: Add null pointer check at function entry:
```c
if (argc < 1 || argv == NULL || argv[0] == NULL) {
    PRINT_USAGE_EXIT("Usage: xpon <action> [options...]\n");
}
```

## Utility Commands

### Check if File Has Debug Symbols

```bash
# Method 1: file command
file <path>
# "not stripped" = has symbols
# "stripped" = no symbols

# Method 2: readelf for debug sections
readelf -S <path> | grep debug
# Look for .debug_info, .debug_line sections

# Method 3: Check BuildID
readelf -n <path> | grep BuildID
```

### Find Source File in DBGROOT

```bash
find $DBGROOT -name "<filename>.c" 2>/dev/null
```

### Verify SONAME

```bash
readelf -d <library> | grep SONAME
```

## Pre-Flight Checklist

Before debugging, verify:

- [ ] Core dump file exists and is readable
- [ ] DBGROOT contains complete filesystem
- [ ] Debug symbols in `.debug/` subdirectories
- [ ] Stripped files in normal directories
- [ ] `set sysroot` points to DBGROOT
- [ ] `file` command loads main executable
- [ ] `core` command loads core dump
- [ ] `info sharedlibrary` shows main libraries with "Yes"

## Project-Specific Paths

| Component | Path |
|-----------|------|
| Core file | `/home/oreo/gdb/core.bcmolt_netconf.unpacked` |
| DBGROOT | `/home/oreo/gdb/20260514.014942` |
| Executable | `$DBGROOT/usr/bin/bcmolt_netconf_server` |
| Debug symbols | `$DBGROOT/usr/bin/.debug/bcmolt_netconf_server` |
| Source code | `$DBGROOT/usr/src/debug/` |
| xpon source | `$DBGROOT/usr/src/debug/netconf-polt/.../bbf-xpon/` |

## Additional Resources

See `~/xpon-core-dump-debug-skills.md` for complete documentation including:
- Detailed setup instructions
- Full crash analysis report
- Source code references
