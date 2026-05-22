#!/bin/bash
# Symlink build/compile_commands.json to each externalsrc repo root for clangd.
#
# Usage:
#   ./setup-compile-commands.sh              # symlink (default; bitbake already built)
#   ./setup-compile-commands.sh netconf-polt # one repo
#   ./setup-compile-commands.sh --export     # re-run cmake export, then symlink
set -euo pipefail

SRCROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILDDIR="$(cd "${SRCROOT}/../.." && pwd)"
REPOS=(netconf-polt xpon-apps xpon-libs)

find_yocto_cmake() {
	local recipe="${1:-netconf-polt}"
	local cmake=""

	if [[ -d "${BUILDDIR}/tmp/work" ]]; then
		cmake="$(
			find "${BUILDDIR}/tmp/work" \
				-path "*/${recipe}/*/recipe-sysroot-native/usr/bin/cmake" \
				2>/dev/null | head -1
		)"
		if [[ -z "${cmake}" ]]; then
			cmake="$(
				find "${BUILDDIR}/tmp/work" \
					-path '*/recipe-sysroot-native/usr/bin/cmake' \
					2>/dev/null | head -1
			)"
		fi
	fi

	if [[ -n "${cmake}" && -x "${cmake}" ]]; then
		echo "${cmake}"
		return 0
	fi

	if command -v cmake >/dev/null 2>&1; then
		command -v cmake
		return 0
	fi

	return 1
}

link_compile_commands() {
	local repos=("$@")

	for repo in "${repos[@]}"; do
		local build_db="${SRCROOT}/${repo}/build/compile_commands.json"
		local link="${SRCROOT}/${repo}/compile_commands.json"
		if [[ -f "${build_db}" ]]; then
			ln -sf build/compile_commands.json "${link}"
			echo "OK ${repo}: compile_commands.json -> build/compile_commands.json"
		else
			echo "SKIP ${repo}: no ${build_db} (bitbake ${repo} first, or use --export)"
		fi
	done
}

export_compile_commands() {
	local repos=("$@")

	if ! CMAKE="$(find_yocto_cmake netconf-polt)"; then
		echo "ERROR: cmake not found under ${BUILDDIR}/tmp/work and not in PATH" >&2
		exit 1
	fi
	echo "Using cmake: ${CMAKE}"

	for repo in "${repos[@]}"; do
		local build_dir="${SRCROOT}/${repo}/build"
		if [[ ! -f "${build_dir}/CMakeCache.txt" ]]; then
			echo "SKIP ${repo}: no ${build_dir}/CMakeCache.txt"
			continue
		fi
		echo "EXPORT ${repo}..."
		( cd "${build_dir}" && "${CMAKE}" -DCMAKE_EXPORT_COMPILE_COMMANDS=ON . )
	done
}

do_export=0
repos=()

for arg in "$@"; do
	case "${arg}" in
		--export) do_export=1 ;;
		*) repos+=("${arg}") ;;
	esac
done

if [[ ${#repos[@]} -eq 0 ]]; then
	repos=("${REPOS[@]}")
fi

if [[ ${do_export} -eq 1 ]]; then
	export_compile_commands "${repos[@]}"
fi

link_compile_commands "${repos[@]}"
