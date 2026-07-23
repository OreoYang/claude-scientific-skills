#!/bin/bash
# Print export for SKILL_ROOT (directory containing SKILL.md).
#
# Usage from workspace:
#   eval "$(bash /path/to/xpon-coredump-debug/scripts/skill_root.sh)"
#   bash "$SKILL_ROOT/scripts/setup_dbgroot.sh" ...

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "export SKILL_ROOT=$ROOT"
