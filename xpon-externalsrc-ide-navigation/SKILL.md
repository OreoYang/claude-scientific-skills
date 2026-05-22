---
name: xpon-externalsrc-ide-navigation
description: >-
  Configures Cursor/VS Code clangd navigation (Go to Definition, #include jump)
  for XPON Yocto externalsrc trees under build-xpon/workspace/sources. Use when
  the user cannot jump into headers like bcmos_system.h, asks about
  compile_commands.json, clangd, multi-root .code-workspace, or IDE IntelliSense
  for netconf-polt, xpon-apps, or xpon-libs.
version: 1.0.0
---

# XPON externalsrc IDE navigation (clangd)

## Root cause

Headers such as `bcmos_system.h` live in the **Yocto recipe sysroot**, not in git source:

- Example: `.../recipe-sysroot/usr/include/bal_api/bcmos_system.h`
- CMake adds `-I${SYSROOT}/usr/include/bal_api` (see `include_directories` in each repo's top `CMakeLists.txt`)

BitBake/CMake resolve includes; **clangd does not** until `compile_commands.json` exists and Cursor uses it.

## Paths (this user's layout)

| Item | Path |
|------|------|
| externalsrc root | `/home/oreo/works/repo/build-xpon/workspace/sources` |
| Multi-root workspace | `.../sources/xpon-externalsrc.code-workspace` |
| Symlink helper script | `.../sources/setup-compile-commands.sh` |
| Native cmake (when not in PATH) | `.../tmp/work/exs1610-vcm-linux/netconf-polt/0.0+git/recipe-sysroot-native/usr/bin/cmake` |

Repos with C/C++ CMake: `netconf-polt`, `xpon-apps`, `xpon-libs`. Optional in workspace: `xpon-protos`, `xpon-yang` (often no compile DB needed).

## Quick fix checklist

When `#include` or **Go to Definition (F12)** fails:

1. Confirm **clangd** extension is active; disable conflicting **C/C++** IntelliSense (`C_Cpp.intelliSenseEngine`: `disabled`).
2. Ensure `build/compile_commands.json` exists for that repo.
3. Symlink at repo root: `compile_commands.json` → `build/compile_commands.json` (run `setup-compile-commands.sh`).
4. Open **`xpon-externalsrc.code-workspace`** (multi-root), not a single subfolder only.
5. **clangd: Restart language server** or **Reload Window**.

## Generate compile_commands.json (per repo)

Prerequisite: configured CMake build dir `<repo>/build` (from BitBake externalsrc or local cmake).

```bash
CMAKE=/home/oreo/works/repo/build-xpon/tmp/work/exs1610-vcm-linux/netconf-polt/0.0+git/recipe-sysroot-native/usr/bin/cmake
cd /home/oreo/works/repo/build-xpon/workspace/sources/<repo>/build
"$CMAKE" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON .
```

Then link for clangd:

```bash
/home/oreo/works/repo/build-xpon/workspace/sources/setup-compile-commands.sh
```

Or per repo:

```bash
cd .../sources/<repo>
ln -sf build/compile_commands.json compile_commands.json
```

After BitBake cleans/rebuilds, `tmp/work/.../0.0+git/` may change — re-run cmake export in that repo's `build/`.

## Multi-root workspace (recommended — scheme D)

**File:** `build-xpon/workspace/sources/xpon-externalsrc.code-workspace`

**Open in Cursor:**

- **File → Open Workspace from File…** → select that `.code-workspace`, or
- `cursor /home/oreo/works/repo/build-xpon/workspace/sources/xpon-externalsrc.code-workspace`

Each folder root gets its own `${workspaceFolder}`; clangd uses `--compile-commands-dir=${workspaceFolder}` (expects `compile_commands.json` at each repo root).

Workspace template (already on disk; extend `folders` if repos are added):

```json
{
  "folders": [
    { "path": "netconf-polt", "name": "netconf-polt" },
    { "path": "xpon-apps", "name": "xpon-apps" },
    { "path": "xpon-libs", "name": "xpon-libs" },
    { "path": "xpon-protos", "name": "xpon-protos" },
    { "path": "xpon-yang", "name": "xpon-yang" }
  ],
  "settings": {
    "C_Cpp.intelliSenseEngine": "disabled",
    "clangd.arguments": [
      "--compile-commands-dir=${workspaceFolder}",
      "--background-index",
      "--clang-tidy=false"
    ]
  },
  "extensions": {
    "recommendations": ["llvm-vs-code-extensions.vscode-clangd"]
  }
}
```

## Alternatives (single `sources/` root)

**Per-repo `.clangd`** at `sources/.clangd` with `PathMatch` + `CompilationDatabase: <repo>/build` — see [reference.md](reference.md).

**Merge** all `*/build/compile_commands.json` into `sources/compile_commands.json` — one DB for one folder workspace; re-run merge after any repo rebuild.

## Agent actions

When the user reports broken navigation:

1. Check `ls <repo>/build/compile_commands.json` and `<repo>/compile_commands.json`.
2. If missing, run cmake export (use native cmake path above if `cmake` not in PATH).
3. Run `setup-compile-commands.sh` or create symlinks.
4. Remind to open `xpon-externalsrc.code-workspace` and restart clangd.
5. Verify one entry in compile DB contains `-I.../bal_api` for the file being edited (e.g. `bcmolt_netconf_server.c`).

Do not commit `compile_commands.json` symlinks unless the team agrees; they are local IDE artifacts.

## Additional resources

- PathMatch / merge details: [reference.md](reference.md)
