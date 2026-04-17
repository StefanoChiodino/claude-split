#!/bin/sh
# Prevent direct writes to board.yaml — all board mutations must go through the split-board CLI.
# This hook runs on PreToolUse for Write and Edit tools.
# Claude Code passes hook input as JSON on stdin: {"tool_name": "...", "tool_input": {...}}

INPUT="$(cat)"
if command -v jq >/dev/null 2>&1; then
  file_path=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // empty' 2>/dev/null)
else
  file_path="$INPUT"
fi

# Check if the tool input targets board.yaml inside a split directory
case "$file_path" in
  *split/active/*/board.yaml*|*split/archive/*/board.yaml*)
    echo "BLOCK: Direct writes to board.yaml are not allowed. Use the split-board CLI to modify board state." >&2
    exit 1
    ;;
esac

exit 0
