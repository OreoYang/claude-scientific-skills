#!/bin/bash
# Extract debug symbols and optional RAUC rootfs into DBGROOT.
#
# Usage:
#   setup_dbgroot.sh [--dbgroot DIR] DBG_TAR [RAUCB]
#
# Example:
#   setup_dbgroot.sh --dbgroot "$(pwd)/dbgroot" *.dbg.tar.bz2 *.raucb

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

DBGROOT="$(pwd)/dbgroot"
DBG_TAR=""
RAUCB=""

usage() {
    cat <<'EOF'
Usage: setup_dbgroot.sh [--dbgroot DIR] DBG_TAR [RAUCB]

  DBG_TAR   Path or glob to *.dbg.tar.bz2 (debug symbols package)
  RAUCB     Optional path or glob to *.raucb (extracts rootfs into DBGROOT)

Environment:
  DBGROOT defaults to $(pwd)/dbgroot — use workspace path, not /tmp.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dbgroot)
            DBGROOT="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            break
            ;;
        -*)
            die "Unknown option: $1"
            ;;
        *)
            if [[ -z "$DBG_TAR" ]]; then
                DBG_TAR="$1"
            elif [[ -z "$RAUCB" ]]; then
                RAUCB="$1"
            else
                die "Unexpected argument: $1"
            fi
            shift
            ;;
    esac
done

[[ -n "$DBG_TAR" ]] || { usage; die "DBG_TAR is required"; }

DBG_TAR=$(resolve_one_file "$DBG_TAR" "debug symbols archive")
mkdir -p "$DBGROOT"

log_info "Extracting debug symbols: $DBG_TAR -> $DBGROOT"
require_cmd tar
tar -xjf "$DBG_TAR" -C "$DBGROOT"

if [[ -n "$RAUCB" ]]; then
    RAUCB=$(resolve_one_file "$RAUCB" "RAUC bundle")
    require_cmd unsquashfs
  require_cmd tar

    local_temp="$DBGROOT/rauc_temp"
    rm -rf "$local_temp"
    mkdir -p "$local_temp"

    log_info "Extracting RAUC bundle: $RAUCB"
    unsquashfs -f -d "$local_temp" "$RAUCB"

    rootfs_tar=$(find "$local_temp" -maxdepth 1 -name '*.rootfs.tar.bz2' -print -quit)
    [[ -n "$rootfs_tar" ]] || die "No *.rootfs.tar.bz2 found inside RAUC bundle"

    log_info "Extracting rootfs: $rootfs_tar -> $DBGROOT"
    tar -xjf "$rootfs_tar" -C "$DBGROOT"
    rm -rf "$local_temp"
fi

log_info "DBGROOT ready: $DBGROOT"
bash "$SCRIPT_DIR/verify_dbgroot.sh" --dbgroot "$DBGROOT"
