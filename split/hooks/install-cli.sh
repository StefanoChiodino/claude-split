#!/bin/sh
# Auto-approve split-board commands in this project on session start.
# The split-board binary is provided via split/bin/split-board (in PATH
# automatically via Claude Code's plugin bin/ mechanism) and installs lazily
# on first use via uv run. No PATH or venv management needed here.

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"
PERM='Bash(split-board:*)'

# If we can't find the project root, bail — nothing to configure.
[ -z "$PROJECT_ROOT" ] && exit 0

SETTINGS_FILE="$PROJECT_ROOT/.claude/settings.local.json"

if [ -f "$SETTINGS_FILE" ]; then
  if ! grep -q 'split-board' "$SETTINGS_FILE" 2>/dev/null; then
    if command -v jq >/dev/null 2>&1; then
      jq --arg p "$PERM" '.permissions.allow += [$p]' "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" \
        && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    fi
  fi
else
  mkdir -p "$(dirname "$SETTINGS_FILE")"
  printf '{\n  "permissions": {\n    "allow": [\n      "%s"\n    ]\n  }\n}\n' "$PERM" > "$SETTINGS_FILE"
fi
