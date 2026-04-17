#!/bin/sh
# Auto-approve Bash(split-board:*) permission requests for the split plugin.
INPUT="$(cat)"
if command -v jq >/dev/null 2>&1; then
  cmd=$(printf '%s' "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
else
  cmd=""
fi
case "$cmd" in
  split-board*)
    printf '{"decision":"allow","reason":"split-board is the Split plugin CLI"}\n'
    exit 0
    ;;
esac
# Pass through — no decision
exit 0
