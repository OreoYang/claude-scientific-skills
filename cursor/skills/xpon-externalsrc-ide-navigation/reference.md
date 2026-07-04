# Reference: other compile DB layouts

Paths below are relative to **`build-xpon/workspace/sources/`** unless noted.

## setup-compile-commands.sh (--export)

Default mode only symlinks. `--export` re-runs cmake in each repo's `build/`:

```bash
./setup-compile-commands.sh --export
./setup-compile-commands.sh --export netconf-polt
```

Requires `<repo>/build/CMakeCache.txt` (from bitbake configure). Finds native cmake under `build-xpon/tmp/work/.../recipe-sysroot-native/usr/bin/cmake`.

CMake warnings (e.g. missing libyang in xpon-apps/event-monitor) are usually non-fatal; symlink step still runs.

## sources/.clangd (single workspace folder)

Place at `sources/.clangd`:

```yaml
---
If:
  PathMatch: netconf-polt/.*
CompileFlags:
  CompilationDatabase: netconf-polt/build

---
If:
  PathMatch: xpon-apps/.*
CompileFlags:
  CompilationDatabase: xpon-apps/build

---
If:
  PathMatch: xpon-libs/.*
CompileFlags:
  CompilationDatabase: xpon-libs/build
```

Paths are relative to the `.clangd` file directory. Points at `build/` directly — no root symlink needed.

## Merge compile_commands.json

From `sources/`:

```bash
SRCROOT="$(pwd)"
python3 - <<'PY'
import json, glob, os
srcroot = os.environ["SRCROOT"]
entries = []
for path in sorted(glob.glob(os.path.join(srcroot, "*/build/compile_commands.json"))):
    with open(path) as f:
        entries.extend(json.load(f))
out = os.path.join(srcroot, "compile_commands.json")
with open(out, "w") as f:
    json.dump(entries, f, indent=2)
print(f"merged {len(entries)} entries -> {out}")
PY
```

## Microsoft C/C++ extension only

Per workspace folder `.vscode/settings.json`:

```json
{
  "C_Cpp.default.compileCommands": "${workspaceFolder}/compile_commands.json"
}
```

Prefer clangd for this stack; avoid running both engines on the same files.

## Sysroot header location

Relative to `build-xpon/`:

- Stable BAL headers: `tmp/sysroots-components/<machine>/sw-bcm686olt/usr/include/bal_api/`
- Per-recipe sysroot: `tmp/work/<machine>-vcm-linux/<recipe>/0.0+git/recipe-sysroot/usr/include/bal_api/`
- Native cmake (`--export` only): `tmp/work/.../<recipe>/0.0+git/recipe-sysroot-native/usr/bin/cmake`
