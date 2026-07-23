#!/bin/bash
# Run GDB batch backtrace with standard XPON settings.
#
# Usage:
#   gdb_bt.sh [--dbgroot DIR] [--binary REL|ABS] [--thread N] [--depth N]
#             [--interactive] CORE_FILE
#
# Default: thread 1, depth 40, batch mode.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

DBGROOT="$(pwd)/dbgroot"
BINARY_REL=""
THREAD=1
DEPTH=40
INTERACTIVE=0
CORE=""

GDB="${GDB:-/usr/bin/gdb}"

usage() {
    cat <<'EOF'
Usage: gdb_bt.sh [options] CORE_FILE

Options:
  --dbgroot DIR     DBGROOT path (default: $(pwd)/dbgroot)
  --binary PATH     Executable relative to DBGROOT or absolute path
  --thread N        Thread for backtrace (default: 1)
  --depth N         Backtrace depth (default: 40)
  --interactive     Run interactive GDB instead of batch
  -h, --help        Show this help

Also runs: info threads, info sharedlibrary (batch mode).
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dbgroot)
            DBGROOT="$2"
            shift 2
            ;;
        --binary)
            BINARY_REL="$2"
            shift 2
            ;;
        --thread)
            THREAD="$2"
            shift 2
            ;;
        --depth)
            DEPTH="$2"
            shift 2
            ;;
        --interactive)
            INTERACTIVE=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            die "Unknown option: $1"
            ;;
        *)
            [[ -z "$CORE" ]] || die "Unexpected argument: $1"
            CORE="$1"
            shift
            ;;
    esac
done

[[ -n "$CORE" ]] || { usage; die "CORE_FILE is required"; }
[[ -f "$CORE" ]] || die "Core file not found: $CORE"
[[ -d "$DBGROOT" ]] || die "DBGROOT not found: $DBGROOT"
if [[ -x "$GDB" ]]; then
    :
elif command -v "$GDB" >/dev/null 2>&1; then
    GDB=$(command -v "$GDB")
else
    die "gdb not found: $GDB"
fi

if [[ -z "$BINARY_REL" ]]; then
    BINARY_REL=$(detect_binary_relpath "$CORE" || true)
    [[ -n "$BINARY_REL" ]] || die "Cannot detect binary — pass --binary"
fi

if [[ "$BINARY_REL" == /* ]]; then
    BINARY_ABS="$BINARY_REL"
else
    BINARY_ABS="$DBGROOT/$BINARY_REL"
fi

[[ -f "$BINARY_ABS" ]] || die "Binary not found: $BINARY_ABS"

log_info "GDB analysis"
log_info "  DBGROOT:  $DBGROOT"
log_info "  Binary:   $BINARY_ABS"
log_info "  Core:     $CORE"
log_info "  Thread:   $THREAD"
log_info "  Depth:    $DEPTH"

if [[ $INTERACTIVE -eq 1 ]]; then
    exec "$GDB" --nh --nx -q \
        -ex "set debuginfod enabled off" \
        -ex "set auto-load safe-path /" \
        -ex "set sysroot $DBGROOT" \
        -ex "file $BINARY_ABS" \
        -ex "core $CORE" \
        -ex "thread $THREAD"
fi

"$GDB" --nh --nx -q -batch \
    -ex "set debuginfod enabled off" \
    -ex "set auto-load safe-path /" \
    -ex "set sysroot $DBGROOT" \
    -ex "file $BINARY_ABS" \
    -ex "core $CORE" \
    -ex "info threads" \
    -ex "thread $THREAD" \
    -ex "bt $DEPTH" \
    -ex "info sharedlibrary"
