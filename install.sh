#!/usr/bin/env bash
# Install shared-workflow commands from one maintained source tree.
set -euo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKFLOW_USER_HOME="${WORKFLOW_USER_HOME:-$HOME}"
export WORKFLOW_USER_HOME
BIN_DIR="${WORKFLOW_BIN_DIR:-$WORKFLOW_USER_HOME/.local/bin}"
STATE_DIR="${DESK_STATE_DIR:-$WORKFLOW_USER_HOME/.local/state/baton}"
for argument in "$@"; do
  case "$argument" in
    --instructions) ;;
    *) printf 'Unknown installation option: %s\n' "$argument" >&2; exit 2 ;;
  esac
done
BACKUP_DIR="$STATE_DIR/recovery/install-$(date +%Y%m%d-%H%M%S)-$$"
mkdir -p "$BIN_DIR"
for name in desk map mem launch-ai; do
  source="$REPO_DIR/bin/$name"
  [ "$name" != launch-ai ] || source="$REPO_DIR/desktop/$name"
  target="$BIN_DIR/$name"
  if [ -e "$target" ] || [ -L "$target" ]; then
    [ "$(readlink "$target" 2>/dev/null || true)" != "$source" ] || continue
    mkdir -p "$BACKUP_DIR/commands"
    cp -a "$target" "$BACKUP_DIR/commands/$name"
  fi
  ln -sfn "$source" "$target"
done
for argument in "$@"; do
  case "$argument" in
    --instructions) python3 "$REPO_DIR/scripts/configure-workflow.py" ;;
    *) printf 'Unknown installation option: %s\n' "$argument" >&2; exit 2 ;;
  esac
done
printf 'Installed commands link to %s/bin\n' "$REPO_DIR"
if [ -d "$BACKUP_DIR" ]; then
  printf 'Replaced command files are saved in %s\n' "$BACKUP_DIR"
fi
