# Split

Turn a single Claude Code session into a team of specialized personas coordinated through a kanban board.

Split assigns work to personas like SME, Tech Lead, Senior Dev, Test Writer, Code Reviewer, and more — each with defined responsibilities and boundaries. An orchestrator dispatches tickets, tracks progress on a board, and enforces a spec-first, test-first workflow.

## Install

```sh
claude plugin marketplace add StefanoChiodino/claude-split
claude plugin install split@claude-split
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

## Updating

Plugins are pinned to the cached version when installed — Claude Code does not auto-update them. To get the latest version:

```sh
claude plugin update split
```

If that doesn't pick up changes, do a clean reinstall:

```sh
claude plugin uninstall split
claude plugin marketplace update claude-split
claude plugin install split@claude-split
```

## Local development

Clone the repo, add it as a local marketplace, then install:

```sh
claude plugin marketplace add /path/to/claude-split
claude plugin install split@claude-split
```

To uninstall:

```sh
claude plugin uninstall split
```

## Dashboard

The `split-board` CLI is installed globally on first Claude Code session via `uv tool install`. After that, it works in any terminal and any project:

```sh
split-board dashboard
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- Requires [uv](https://docs.astral.sh/uv/) — install it before using the plugin.

## Known limitations

- **Permission prompts**: Claude Code requires approval for each tool type (Write, Edit, WebSearch, etc.) when agents run. This is a platform restriction for marketplace plugins — there is currently no way to pre-approve tools on a per-plugin basis. Approve once per session when prompted.
- **Git isolation**: Each ticket runs in its own git worktree. Agents collaborate through branches and merges — they never share a working directory. All work is committed and merged back to the split branch, then integrated into main at the end.
