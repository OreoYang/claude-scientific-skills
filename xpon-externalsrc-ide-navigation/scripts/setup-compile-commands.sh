#!/bin/bash
# Link build/compile_commands.json to each repo root for clangd / Cursor.
# Default SRCROOT: XPON externalsrc tree for this user.
set -euo pipefail

SRCROOT="${SRCROOT:-/home/oreo/works/repo/build-xpon/workspace/sources}"

for repo in netconf-polt xpon-apps xpon-libs; do
	build_db="${SRCROOT}/${repo}/build/compile_commands.json"
	link="${SRCROOT}/${repo}/compile_commands.json"
	if [[ -f "${build_db}" ]]; then
		ln -sf build/compile_commands.json "${link}"
		echo "OK ${repo}: compile_commands.json -> build/compile_commands.json"
	else
		echo "SKIP ${repo}: no ${build_db}"
		echo "      Run: cd ${SRCROOT}/${repo}/build && cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=ON ."
	fi
done
