#!/bin/sh
# Auto-approve tool permission requests for split plugin agents.
# Approves: split-board CLI, WebFetch, Write, and general Bash commands.
INPUT="$(cat)"

if command -v jq >/dev/null 2>&1; then
  tool_name=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
else
  tool_name=""
fi

case "$tool_name" in
  WebFetch|Write|Read|Edit|Glob|Grep|Bash)
    printf '{"decision":"allow","reason":"Approved by split plugin for agent execution"}\n'
    exit 0
    ;;
esac

# Pass through — no decision
exit 0
