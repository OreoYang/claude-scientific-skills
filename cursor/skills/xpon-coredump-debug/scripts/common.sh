#!/bin/bash
# Shared helpers for xpon-coredump-debug skill scripts.

set -euo pipefail

log_info()  { echo "[INFO]  $*" >&2; }
log_warn()  { echo "[WARN]  $*" >&2; }
log_error() { echo "[ERROR] $*" >&2; }

die() {
    log_error "$@"
    exit 1
}

require_cmd() {
    local cmd="$1"
    command -v "$cmd" >/dev/null 2>&1 || die "Required command not found: $cmd (see prerequisites.md)"
}

require_file() {
    local path="$1"
    local desc="${2:-file}"
    [[ -f "$path" ]] || die "Missing $desc: $path"
}

require_dir() {
    local path="$1"
    local label="${2:-directory}"
    [[ -d "$path" ]] || die "Missing $label: $path"
}

# Resolve entra_rpd_decrypt: prefer PATH, then /usr/local/bin.
resolve_decrypt_cmd() {
    if command -v entra_rpd_decrypt >/dev/null 2>&1; then
        command -v entra_rpd_decrypt
    elif [[ -x /usr/local/bin/entra_rpd_decrypt ]]; then
        echo /usr/local/bin/entra_rpd_decrypt
    else
        die "entra_rpd_decrypt not found (see prerequisites.md)"
    fi
}

# Expand single path or glob to one existing file.
resolve_one_file() {
    local pattern="$1"
    local desc="$2"
    local -a matches=()

    if [[ -f "$pattern" ]]; then
        echo "$pattern"
        return 0
    fi

    shopt -s nullglob
    matches=( $pattern )
    shopt -u nullglob

    if [[ ${#matches[@]} -eq 0 ]]; then
        die "No $desc found for: $pattern"
    fi
    if [[ ${#matches[@]} -gt 1 ]]; then
        die "Multiple $desc match '$pattern' — pass an explicit path"
    fi
    echo "${matches[0]}"
}

# Relative binary path under DBGROOT (e.g. usr/bin/bcmolt_netconf_server).
detect_binary_relpath() {
    local core_path="$1"
    local base
    base=$(basename "$core_path")

    case "$base" in
        core.bcmolt_netconf.*)
            echo "usr/bin/bcmolt_netconf_server"
            ;;
        core.lag.*)
            echo "usr/bin/lag"
            ;;
        core.bcmoni*)
            echo "usr/bin/bcmoni"
            ;;
        core.protocol*)
            echo "usr/bin/protocol-handler"
            ;;
        core.bcmolt*)
            echo "usr/bin/bcmolt_netconf_server"
            ;;
        *)
            echo ""
            ;;
    esac
}
