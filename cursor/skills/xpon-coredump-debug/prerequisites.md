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

`entra_rpd_decrypt` requires:

```
/decrypt_keys/dorado_private.pem
```

This key is **not** distributed with the skill. Obtain from your team's secure key store.

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
