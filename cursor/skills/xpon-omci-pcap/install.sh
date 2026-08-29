#!/usr/bin/env bash
# Install xpon-omci-pcap Cursor skill (personal or project scope).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${1:-$HOME/.cursor/skills/xpon-omci-pcap}"

mkdir -p "$(dirname "$TARGET")"
if [[ -e "$TARGET" && ! -L "$TARGET" ]]; then
  echo "Target exists: $TARGET (remove or pass a different path)" >&2
  exit 1
fi

if [[ -L "$TARGET" ]]; then
  rm "$TARGET"
fi

if [[ "$TARGET" == "$SCRIPT_DIR" ]]; then
  echo "Already at install location: $TARGET"
else
  ln -sfn "$SCRIPT_DIR" "$TARGET"
  echo "Linked $SCRIPT_DIR -> $TARGET"
fi

chmod +x "$TARGET/scripts/journal_to_omci_pcap.py"
echo "Done. Skill: xpon-omci-pcap (see SKILL.md)"
