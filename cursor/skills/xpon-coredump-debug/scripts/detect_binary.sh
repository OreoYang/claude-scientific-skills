#!/bin/bash
# Map core filename to executable path relative to DBGROOT.
#
# Usage:
#   detect_binary.sh CORE_FILE [DBGROOT]
#
# Prints relative path (e.g. usr/bin/bcmolt_netconf_server) or exits 1.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

CORE="${1:-}"
DBGROOT="${2:-}"

usage() {
    cat <<'EOF'
Usage: detect_binary.sh CORE_FILE [DBGROOT]

Prints executable path relative to DBGROOT based on core filename pattern.
Exits 1 if pattern is unknown or binary missing from DBGROOT.
EOF
}

if [[ -z "$CORE" ]]; then
    usage
    exit 1
fi

[[ -f "$CORE" ]] || die "Core file not found: $CORE"

REL=$(detect_binary_relpath "$CORE")
[[ -n "$REL" ]] || die "Unknown core filename pattern: $(basename "$CORE") (use gdb_bt.sh --binary)"

if [[ -n "$DBGROOT" ]]; then
    if [[ -f "$DBGROOT/$REL" ]]; then
        echo "$REL"
        exit 0
    fi
    # Try .debug path as hint
    dir_part=$(dirname "$REL")
    base_part=$(basename "$REL")
    if [[ -f "$DBGROOT/$dir_part/.debug/$base_part" ]]; then
        echo "$REL"
        exit 0
    fi
    die "Binary not found under DBGROOT: $DBGROOT/$REL"
fi

echo "$REL"
