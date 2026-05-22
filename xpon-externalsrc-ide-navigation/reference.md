# Reference: other compile DB layouts

## sources/.clangd (single workspace folder)

Place at `/home/oreo/works/repo/build-xpon/workspace/sources/.clangd`:

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

Paths are relative to the `.clangd` file directory.

## Merge compile_commands.json

```bash
SRCROOT=/home/oreo/works/repo/build-xpon/workspace/sources
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

Stable BAL headers (example):

`/home/oreo/works/repo/build-xpon/tmp/sysroots-components/exs1610/sw-bcm686olt/usr/include/bal_api/`

Per-recipe sysroot (matches active BitBake build):

`/home/oreo/works/repo/build-xpon/tmp/work/exs1610-vcm-linux/<recipe>/0.0+git/recipe-sysroot/usr/include/bal_api/`
