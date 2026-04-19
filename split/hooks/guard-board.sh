#!/bin/sh
# Prevent direct writes to .claude/split/ — all mutations must go through the split-board CLI.
# This hook runs on PreToolUse for Write, Edit, and Bash tools.
# Claude Code passes hook input as JSON on stdin: {"tool_name": "...", "tool_input": {...}}

INPUT="$(cat)"
TOOL_NAME=""
TARGET=""

if command -v jq >/dev/null 2>&1; then
  TOOL_NAME=$(printf '%s' "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null)
  TARGET=$(printf '%s' "$INPUT" | jq -r '.tool_input.file_path // .tool_input.path // .tool_input.command // empty' 2>/dev/null)
else
  TARGET="$INPUT"
fi

case "$TOOL_NAME" in
  Bash)
    # Allow split-board CLI commands — they are the sanctioned interface
    case "$TARGET" in
      *split-board*) exit 0 ;;
    esac
    # Block any bash command that references .claude/split with a write-like operation
    if printf '%s' "$TARGET" | grep -qE '\.claude/split' ; then
      echo "BLOCK: Direct file operations on .claude/split/ are forbidden. Use split-board CLI commands instead." >&2
      exit 1
    fi
    ;;
  *)
    # Write or Edit — block if path is inside .claude/split/
    case "$TARGET" in
      *.claude/split/*)
        echo "BLOCK: Direct writes to .claude/split/ are forbidden. Use split-board CLI commands instead." >&2
        exit 1
        ;;
    esac
    ;;
esac

exit 0
