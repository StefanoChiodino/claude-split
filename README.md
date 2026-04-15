# Split

Turn a single Claude Code session into a team of specialized personas coordinated through a kanban board.

Split assigns work to personas like SME, Tech Lead, Senior Dev, Test Writer, Code Reviewer, and more — each with defined responsibilities and boundaries. An orchestrator dispatches tickets, tracks progress on a board, and enforces a spec-first, test-first workflow.

## Install

Inside Claude:

```
/plugin marketplace add StefanoChiodino/claude-split
/plugin install split@claude-split
```

Or from the terminal:

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

## Dashboard

A live Textual TUI for monitoring board state — kanban columns (BACKLOG / ACTIVE / APPROVAL / DONE), recent activity, and metrics.

```sh
split-board dashboard          # all active specs (press `s` to cycle)
split-board dashboard --spec S001
```

Keys: `q` quits, `s` cycles between specs.

> Currently `split-board` is not yet exposed on `PATH` from the published plugin. Until that's fixed, run it from the repo with `uv run --project split/tools split-board dashboard`, or invoke the wrapper installed under `~/.claude/plugins/data/split-claude-split/.venv/bin/split-board`.

## Local development

Inside Claude:

```
/plugin marketplace add StefanoChiodino/claude-split
/plugin install split@claude-split
```

Or from the terminal:

```sh
claude plugin marketplace add StefanoChiodino/claude-split
claude plugin install split@claude-split
```

To fully reset:

Inside Claude:

```
/plugin uninstall split
```

Or from the terminal:

```sh
claude plugin uninstall split
rm -rf ~/.claude/plugins/cache/claude-split
rm -rf ~/.claude/plugins/marketplaces/claude-split
```

## Requirements

- [Claude Code](https://docs.anthropic.com/en/docs/claude-code)
- [uv](https://docs.astral.sh/uv/) (for the board CLI, installed automatically on session start)
