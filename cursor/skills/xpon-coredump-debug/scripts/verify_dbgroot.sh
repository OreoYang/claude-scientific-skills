#!/bin/bash
# Pre-flight checks for DBGROOT and optional binary.
#
# Usage:
#   verify_dbgroot.sh [--dbgroot DIR] [--binary REL_PATH]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

DBGROOT="$(pwd)/dbgroot"
BINARY_REL="usr/bin/bcmolt_netconf_server"
FAIL=0

usage() {
    cat <<'EOF'
Usage: verify_dbgroot.sh [--dbgroot DIR] [--binary REL_PATH]

Checks DBGROOT layout, stripped/unstripped pairs, and host tools.
Exit 0 if all checks pass; exit 1 otherwise.
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
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            die "Unknown option: $1"
            ;;
        *)
            die "Unexpected argument: $1"
            ;;
    esac
done

check_ok()  { log_info "OK: $*"; }
check_fail(){ log_error "FAIL: $*"; FAIL=1; }

log_info "Verifying DBGROOT: $DBGROOT"

for t in gdb readelf file; do
    command -v "$t" >/dev/null 2>&1 && check_ok "tool $t" || check_fail "missing tool $t"
done

[[ -d "$DBGROOT" ]] && check_ok "DBGROOT exists" || check_fail "DBGROOT missing"

if [[ "$DBGROOT" == /tmp/* ]]; then
    check_fail "DBGROOT is under /tmp — use workspace path for persistence"
fi

STRIPPED="$DBGROOT/$BINARY_REL"
DEBUG_DIR=$(dirname "$BINARY_REL")
DEBUG_BASE=$(basename "$BINARY_REL")
UNSTRIPPED="$DBGROOT/$DEBUG_DIR/.debug/$DEBUG_BASE"

if [[ -f "$STRIPPED" ]]; then
    check_ok "stripped binary: $BINARY_REL"
    if file "$STRIPPED" | grep -q 'ELF'; then
        check_ok "stripped file is ELF"
    else
        check_fail "stripped file is not ELF: $STRIPPED"
    fi
else
    check_fail "stripped binary missing: $STRIPPED"
fi

if [[ -f "$UNSTRIPPED" ]]; then
    check_ok "unstripped binary: $DEBUG_DIR/.debug/$DEBUG_BASE"
    if file "$UNSTRIPPED" | grep -qi 'debug_info\|not stripped'; then
        check_ok "unstripped has debug_info"
    else
        check_warn "unstripped may lack debug_info — check: file $UNSTRIPPED"
    fi
else
    check_fail "unstripped binary missing: $UNSTRIPPED"
fi

if [[ -f "$STRIPPED" ]] && command -v readelf >/dev/null 2>&1; then
    bid_s=$(readelf -n "$STRIPPED" 2>/dev/null | grep -i 'Build ID' | head -1 || true)
    bid_d=$(readelf -n "$UNSTRIPPED" 2>/dev/null | grep -i 'Build ID' | head -1 || true)
    if [[ -n "$bid_s" ]]; then
        check_ok "stripped BuildID: $bid_s"
    fi
    if [[ -n "$bid_s" && -n "$bid_d" && "$bid_s" != "$bid_d" ]]; then
        check_fail "BuildID mismatch between stripped and unstripped"
    fi
fi

if [[ -d "$DBGROOT/usr/lib" ]]; then
    check_ok "usr/lib present"
else
    check_warn "usr/lib missing — rootfs may be incomplete"
fi

if [[ $FAIL -eq 0 ]]; then
    log_info "All critical checks passed"
    exit 0
fi

log_error "Verification failed — see prerequisites.md and reference.md"
exit 1
