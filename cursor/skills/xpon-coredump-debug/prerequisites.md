# Prerequisites

## Host Tools

Install or verify before running skill scripts:

| Tool | Purpose | Typical path |
|------|---------|--------------|
| `gdb` | Core analysis | `/usr/bin/gdb` |
| `entra_rpd_decrypt` | Decrypt support-info-logs | `/usr/local/bin/entra_rpd_decrypt` |
| `unzstd` | Decompress `.zst` cores | `unzstd` on `$PATH` |
| `tar` | Archive extraction | system |
| `unsquashfs` | Extract RAUC bundle | `squashfs-tools` package |
| `readelf` | BuildID verification | `binutils` package |
| `file` | Symbol/debug_info check | system |

Quick check:

```bash
for t in gdb entra_rpd_decrypt unzstd tar unsquashfs readelf file; do
  command -v "$t" || echo "MISSING: $t"
done
```

## Decrypt Key

`entra_rpd_decrypt` reads the RSA private key from a fixed host path:

```
/decrypt_keys/dorado_private.pem
```

This key is **not** distributed with the skill. Obtain from your team's secure key store.

Other keys under `/decrypt_keys/` (e.g. `concierge_private.pem`, `galiano_private.pem`) are for different product lines — use `dorado_private.pem` for EXS1610 / Dorado OLT support dumps.

## Decrypting `support-info-logs.tar.gz`

### Archive layout

```
support-info-logs-*.tar.gz
└── debugdump/
    ├── encrypted.tar.gz.enc   # RSA-encrypted payload (cores, logs, redis, …)
    ├── ENC_AES_KEY            # OLT-side AES key material (do **not** pass to entra_rpd_decrypt)
    └── clear/                 # Non-sensitive collectors (already plaintext)
```

Sensitive data lives inside `encrypted.tar.gz.enc`. After decrypt + extract:

```
debugdump/
├── encrypted.tar.gz           # produced by entra_rpd_decrypt
└── encrypted/
    ├── CoreDump/coredump/     # core.* or core.*.zst
    ├── ExtraLog/
    ├── SystemJournal/
    └── …
```

### Option A — automated (recommended)

```bash
bash "$SKILL_ROOT/scripts/unpack_support.sh" \
  --workdir "$(pwd)/support-debug" \
  /path/to/support-info-logs-*.tar.gz
```

On success prints `CORE=...` and `CORE_DIR=...`. If the OLT had no crash at collection time, `CoreDump/coredump/` may be empty (`list.txt` says "There are no coredumps") — the script exits with an error in that case, but logs under `encrypted/` are still usable.

### Option B — manual steps

```bash
WORKDIR="$(pwd)/support-debug"
ARCHIVE=/path/to/support-info-logs-*.tar.gz

mkdir -p "$WORKDIR"
tar zxf "$ARCHIVE" -C "$WORKDIR"
cd "$WORKDIR/debugdump"

# Decrypt: positional arg only — tool picks up /decrypt_keys/dorado_private.pem
entra_rpd_decrypt encrypted.tar.gz.enc
# → encrypted.tar.gz

tar zxf encrypted.tar.gz
unzstd --rm encrypted/CoreDump/coredump/*.zst   # skip if no .zst files
ls encrypted/CoreDump/coredump/core.*
```

### `entra_rpd_decrypt` usage notes

| Command | Result |
|---------|--------|
| `entra_rpd_decrypt encrypted.tar.gz.enc` | **Correct** — decrypts to `encrypted.tar.gz` in cwd |
| `entra_rpd_decrypt -d encrypted.tar.gz.enc ENC_AES_KEY` | **Wrong** — `ENC_AES_KEY` is not the host RSA key; `-d` also fails on current tool builds |
| `entra_rpd_decrypt -d encrypted.tar.gz.enc /decrypt_keys/dorado_private.pem` | **Wrong** — same CLI parsing issue; key path is not needed when using the default location |

Verify decrypt succeeded:

```bash
test -f encrypted.tar.gz && echo OK
```

## Per-Incident Inputs (user-provided)

| Artifact | Source | Must match |
|----------|--------|------------|
| `*.dbg.tar.bz2` | Yocto build (`bitbake` debug package) | Core BuildID |
| `*.raucb` | RAUC release bundle | Same build as core |
| `support-info-logs-*.tar.gz` | OLT `suppinfo-mgr` / lab download | Crash on that node |
| `core.*` | Unpacked core (or from support archive) | Running binary at crash time |

Build artifacts example locations after `bitbake xpon-olt-bundle`:

- `build-xpon/tmp/deploy/images/exs1610/*.raucb`
- Debug symbols package alongside release artifacts (team mirror / build server)

## Directory Conventions

| Variable | Recommended path | Notes |
|----------|------------------|-------|
| `DBGROOT` | `$(pwd)/dbgroot` | Persistent; IDE-browsable |
| Support workdir | `$(pwd)/support-debug` | Decrypted cores and logs |

**Do not use `/tmp`** — it is wiped on reboot and is not visible in the IDE workspace.

## DBGROOT Layout (after setup)

```
dbgroot/
├── usr/bin/bcmolt_netconf_server          # stripped runtime binary
├── usr/bin/.debug/bcmolt_netconf_server   # unstripped (debug_info)
├── usr/lib/...
├── usr/lib/.debug/...
└── usr/src/debug/...                      # optional source paths for GDB
```

Both stripped and unstripped copies are required for symbol loading with `set sysroot`.

## Related Skills

- **xpon-chicago-lab-debug** — SSH to lab OLT, collect support-info-logs, journalctl
- **Workspace externalsrc** — `netconf-polt`, `xpon-apps` for fix implementation after root-cause analysis
