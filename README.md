# Split

Turn a single Claude Code session into a team of specialized personas coordinated through a kanban board.

Split assigns work to personas like SME, Tech Lead, Senior Dev, Test Writer, Code Reviewer, and more — each with defined responsibilities and boundaries. An orchestrator dispatches tickets, tracks progress on a board, and enforces a spec-first, test-first workflow.

## Install

Inside Claude:

```
/plugin marketplace add StefanoChiodino/claude-split
/plugin install split@claude-split
# Syntax may vary by Claude Code version — check /help if this fails
```

Or from the terminal:

```sh
claude plugin marketplace add StefanoChiodino/claude-split
claude plugin install split@claude-split
# Syntax may vary by Claude Code version — check /help if this fails
```

## Usage

Start a session and invoke the skill:

```
/split
```

The orchestrator will guide you through spec creation, task breakdown, and parallel execution across personas.

## Quick start

Start a new session and invoke Split:

```
You: /split
Claude: What would you like to build?
You: Add rate limiting to the API
[SME] Let me ask a few clarifying questions...
[Board created, tickets dispatched across personas]
```

## Local development

Clone the repo and install from the local path:

```sh
claude plugin install --source /path/to/claude-split/split
```

To uninstall:

```sh
claude plugin uninstall split
```

## Dashboard

The `split-board` CLI is placed on PATH automatically by Claude Code's plugin `bin/` mechanism. If `split-board` is not found, run it via:

```sh
uv run --project split/tools split-board
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Requires [uv](https://docs.astral.sh/uv/) — install it before using the plugin.

## Known limitations

- **Permission prompts**: Claude Code requires approval for each tool type (Write, Edit, WebSearch, etc.) when agents run. This is a platform restriction for marketplace plugins — there is currently no way to pre-approve tools on a per-plugin basis. Approve once per session when prompted.
- **Worktree isolation**: Agent file changes are isolated to a git worktree and do not affect your working tree. However, this is git isolation only — permission prompts still occur normally.
