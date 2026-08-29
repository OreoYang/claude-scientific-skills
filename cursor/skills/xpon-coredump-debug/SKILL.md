---
name: xpon-core-dump-debug
description: >-
  Debug XPON core dumps (bcmolt_netconf_server, lag, bcmoni): setup DBGROOT,
  decrypt support-info-logs, GDB backtrace, root-cause analysis. Use when the
  user mentions core dump, coredump, SIGSEGV, segmentation fault, xpon crash,
  or bcmolt_netconf_server crash on embedded Linux.
version: 2.0.2
---

# xpon Core Dump Debug

Workflow for debugging core dumps from bcmolt_netconf_server and other XPON embedded Linux services.

## Skill Path (do not hardcode `~/.cursor/...`)

Scripts live next to this file under `scripts/`. **Never** bake in a fixed home path like `~/.cursor/skills/xpon-coredump-debug` — installs differ (Cursor personal, Claude Code, project `.cursor/skills/`).

Resolve `SKILL_ROOT` once per session, in order:

1. Directory containing this `SKILL.md` (path from when the skill was loaded)
2. `$XPON_COREDUMP_SKILL_ROOT` if set
3. First existing directory among:
   - `$HOME/.cursor/skills/xpon-coredump-debug`
   - `$HOME/.claude/skills/xpon-core-dump-debug`
   - `<workspace>/.cursor/skills/xpon-coredump-debug`

Then define:

```bash
# Option A: agent already knows SKILL_ROOT from loaded skill path
# Option B: derive from any script (works regardless of install location)
eval "$(bash "$SKILL_ROOT/scripts/skill_root.sh")"
```

All commands below use `"$SKILL_ROOT/scripts/<name>.sh"`. In tables, paths are relative to `SKILL_ROOT` (e.g. `scripts/setup_dbgroot.sh`).

## Before You Start

1. Read [prerequisites.md](prerequisites.md) — tools, keys, build artifacts.
2. Place working directories under the **workspace** (`$(pwd)/dbgroot`, `$(pwd)/support-debug`), never `/tmp`.

## Workflow

```
Task Progress:
- [ ] Resolve SKILL_ROOT
- [ ] Step 1: Setup DBGROOT (debug symbols + rootfs)
- [ ] Step 2: Obtain core file (direct or from support-info-logs)
- [ ] Step 3: Verify environment
- [ ] Step 4: Run GDB backtrace
- [ ] Step 5: Deep analysis + report
```

### Step 1: Setup DBGROOT

Run from the workspace directory where `*.dbg.tar.bz2` and `*.raucb` live:

```bash
bash "$SKILL_ROOT/scripts/setup_dbgroot.sh" \
  --dbgroot "$(pwd)/dbgroot" \
  /path/to/*.dbg.tar.bz2 \
  /path/to/*.raucb
```

`RAUCB` is optional if DBGROOT already has a complete rootfs.

### Step 2a: Core from support-info-logs archive

**Automated** (decrypt `debugdump/encrypted.tar.gz.enc` → extract → `unzstd` cores):

```bash
bash "$SKILL_ROOT/scripts/unpack_support.sh" \
  --workdir "$(pwd)/support-debug" \
  /path/to/support-info-logs-*.tar.gz
```

The script prints `CORE=...` on success. Use that path in later steps.

**Manual decrypt** (same result; see [prerequisites.md](prerequisites.md) for archive layout):

```bash
tar zxf support-info-logs-*.tar.gz -C support-debug
cd support-debug/debugdump
entra_rpd_decrypt encrypted.tar.gz.enc    # → encrypted.tar.gz (uses /decrypt_keys/dorado_private.pem)
tar zxf encrypted.tar.gz
unzstd --rm encrypted/CoreDump/coredump/*.zst
```

Do **not** pass `ENC_AES_KEY` to `entra_rpd_decrypt` — that file is OLT-side metadata, not the host RSA key.

To pull archives from Chicago lab OLT, see `xpon-chicago-lab-debug` skill.

### Step 2b: Core file already available

Skip unpack; note the core path directly.

### Step 3: Verify

```bash
bash "$SKILL_ROOT/scripts/verify_dbgroot.sh" \
  --dbgroot "$(pwd)/dbgroot"

CORE=/path/to/core.*
BINARY=$(bash "$SKILL_ROOT/scripts/detect_binary.sh" \
  "$CORE" "$(pwd)/dbgroot")
echo "BINARY=$BINARY"
```

### Step 4: GDB backtrace

```bash
bash "$SKILL_ROOT/scripts/gdb_bt.sh" \
  --dbgroot "$(pwd)/dbgroot" \
  --binary "$BINARY" \
  --depth 40 \
  "$CORE"
```

For interactive GDB, add `--interactive` or run gdb manually with the same `sysroot` / `file` settings (see [reference.md](reference.md)).

### Step 5: Deep analysis

1. `frame 1` on crash thread; `info args`, `info locals`
2. `info sharedlibrary` — symbols must show **Yes**
3. For ONU/OMCI crashes: `thread apply all bt` (see [reference.md](reference.md))
4. Cross-check source in workspace `externalsrc` or `$DBGROOT/usr/src/debug`
5. Write report using template in [examples/sample-report.md](examples/sample-report.md)

## Utility Scripts

| Script | Purpose |
|--------|---------|
| `scripts/skill_root.sh` | Print `export SKILL_ROOT=...` for the install that contains it |
| `scripts/setup_dbgroot.sh` | Extract `*.dbg.tar.bz2` + optional `*.raucb` → DBGROOT |
| `scripts/unpack_support.sh` | Decrypt/extract support-info-logs → core file |
| `scripts/verify_dbgroot.sh` | Pre-flight: tools, symbols, stripped/unstripped pairs |
| `scripts/detect_binary.sh` | Map `core.*` filename → executable under DBGROOT |
| `scripts/gdb_bt.sh` | Batch GDB backtrace with standard XPON settings |

**Always execute** these scripts via `bash`; do not re-implement their logic inline unless a script flag is missing.

## Additional Resources

| File | Content |
|------|---------|
| [prerequisites.md](prerequisites.md) | Host tools, decrypt key, build artifacts |
| [reference.md](reference.md) | GDB commands, core types, ONU patterns, troubleshooting |
| [examples/sample-report.md](examples/sample-report.md) | Filled-in analysis report example |
