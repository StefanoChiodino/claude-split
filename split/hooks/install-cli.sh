#!/bin/sh
# Install split-board globally so it's available in any terminal/project.
# Works for both marketplace installs (~/.claude/plugins/cache/...) and
# local dev installs (clone path). Resolves the tools dir relative to this hook.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"

if command -v uv >/dev/null 2>&1; then
  uv tool install --force --quiet "$PLUGIN_ROOT/tools" 2>/dev/null || true
fi

echo "Split plugin active. split-board CLI ready."
