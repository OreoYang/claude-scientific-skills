#!/bin/bash
# Decrypt and extract support-info-logs archive to obtain core file(s).
#
# Usage:
#   unpack_support.sh [--workdir DIR] SUPPORT_ARCHIVE.tar.gz
#
# On success prints:
#   CORE=<path-to-first-core>
#   CORE_DIR=<directory-containing-cores>

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "$SCRIPT_DIR/common.sh"

WORKDIR="$(pwd)/support-debug"
ARCHIVE=""

usage() {
    cat <<'EOF'
Usage: unpack_support.sh [--workdir DIR] SUPPORT_ARCHIVE.tar.gz

Decrypts encrypted.tar.gz.enc via entra_rpd_decrypt, extracts cores,
decompresses .zst files. Requires /decrypt_keys/dorado_private.pem.
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --workdir)
            WORKDIR="$2"
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
            [[ -z "$ARCHIVE" ]] || die "Unexpected argument: $1"
            ARCHIVE="$1"
            shift
            ;;
    esac
done

[[ -n "$ARCHIVE" ]] || { usage; die "SUPPORT_ARCHIVE is required"; }
ARCHIVE=$(resolve_one_file "$ARCHIVE" "support-info-logs archive")

require_cmd tar
require_cmd unzstd
DECRYPT_CMD=$(resolve_decrypt_cmd)

[[ -f /decrypt_keys/dorado_private.pem ]] || \
    log_warn "Decrypt key not found at /decrypt_keys/dorado_private.pem — decrypt may fail"

mkdir -p "$WORKDIR"
log_info "Extracting outer archive: $ARCHIVE -> $WORKDIR"
tar zxf "$ARCHIVE" -C "$WORKDIR"

DEBUGDUMP="$WORKDIR/debugdump"
[[ -d "$DEBUGDUMP" ]] || die "Expected debugdump/ inside archive (got: $WORKDIR)"

ENC="$DEBUGDUMP/encrypted.tar.gz.enc"
[[ -f "$ENC" ]] || die "Missing $ENC"

log_info "Decrypting: $ENC"
( cd "$DEBUGDUMP" && "$DECRYPT_CMD" encrypted.tar.gz.enc )

PLAIN="$DEBUGDUMP/encrypted.tar.gz"
[[ -f "$PLAIN" ]] || die "Decrypt did not produce encrypted.tar.gz"

log_info "Extracting encrypted payload"
tar zxf "$PLAIN" -C "$DEBUGDUMP"

CORE_DIR="$DEBUGDUMP/encrypted/CoreDump/coredump"
[[ -d "$CORE_DIR" ]] || die "Missing CoreDump/coredump directory after extract"

shopt -s nullglob
zst_files=( "$CORE_DIR"/*.zst )
shopt -u nullglob

if [[ ${#zst_files[@]} -gt 0 ]]; then
    log_info "Decompressing ${#zst_files[@]} .zst core file(s)"
    unzstd --rm "${zst_files[@]}"
fi

shopt -s nullglob
core_files=( "$CORE_DIR"/core.* )
shopt -u nullglob

[[ ${#core_files[@]} -gt 0 ]] || die "No core.* files found in $CORE_DIR"

# Prefer newest core if multiple exist.
IFS=$'\n' core_files=( $(ls -1t "${core_files[@]}") )
unset IFS

CORE="${core_files[0]}"
log_info "Found ${#core_files[@]} core file(s); primary: $CORE"

echo "CORE_DIR=$CORE_DIR"
echo "CORE=$CORE"
if [[ ${#core_files[@]} -gt 1 ]]; then
    log_info "Additional cores:"
    for c in "${core_files[@]:1}"; do
        echo "CORE_EXTRA=$c"
    done
fi
