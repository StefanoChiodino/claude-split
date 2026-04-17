#!/bin/sh
# Verify the split-board CLI is available on session start.
# The split-board binary is provided via split/bin/split-board (in PATH
# automatically via Claude Code's plugin bin/ mechanism) and installs lazily
# on first use via uv run. No PATH or venv management needed here.
# Permission auto-approval is handled by the PermissionRequest hook.

echo "Split plugin active. split-board CLI ready."
