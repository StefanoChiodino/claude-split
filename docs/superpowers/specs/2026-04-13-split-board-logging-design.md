# Split Board CLI Logging — Design Spec

Adds automatic execution logging to every CLI mutation and a manual `log` command for orchestrator-level events. The CLI becomes the single source of activity history — every state change is recorded in `log.md` with zero caller effort.

## Problem

The CLI creates an empty `log.md` at spec init but nothing writes to it. The SKILL.md instructs the orchestrator to "append to execution log after each action," but this relies on the caller remembering to do it — and they don't. The dashboard's activity feed stays blank.

Meanwhile, the CLI already knows exactly what changed on every mutation. Logging is free observability.

## Design

### Log Helper

A single function in `board.py`:

```python
def append_log(spec_dir: Path, message: str) -> None:
    log_path = spec_dir / "log.md"
    with open(log_path, "a") as f:
        f.write(f"{now_iso()} {message}\n")
```

Every command handler calls `append_log` after a successful mutation. The helper lives alongside `save_board` and `now_iso`.

### Log Format

One line per event, append-only:

```
2026-04-13T19:04:29+00:00 T002 backlog→in_progress @senior-dev
2026-04-13T19:05:12+00:00 T002 artifact: vector_voyage/
2026-04-13T19:06:00+00:00 T003 dispatching to senior-dev agent
2026-04-13T19:10:33+00:00 T003 backlog→in_progress
2026-04-13T19:15:01+00:00 T003 in_progress→done tokens=15230
```

ISO 8601 timestamp, space, descriptive message. Grep-friendly. The dashboard's existing `tail_lines()` reads this without changes.

### Auto-Logged Events

Every mutating command logs after success:

| Command | Log message |
|---|---|
| `spec init` | `S001 created: "Rate Limiting"` |
| `spec archive` | `S001 archived` |
| `spec abandon` | `S001 abandoned` |
| `milestone add` | `M001 added: "Foundation"` |
| `milestone move-ticket` | `T003 moved to M002` |
| `ticket add` | `T005 added to M002: "Implement input handler" @senior-dev` |
| `ticket update --status` | `T002 backlog→in_progress @senior-dev` |
| `ticket update --tokens-used` | `T002 tokens=15230` |
| `ticket update --artifact` | `T002 artifact: vector_voyage/` |
| `ticket update` (combined) | `T002 in_progress→done tokens=15230 artifact: vector_voyage/` |
| `ticket add-dependency` | `T005 dependency added: T003` |
| `ticket remove-dependency` | `T005 dependency removed: T003` |
| `followup create` | `T003a follow-up of T003: "Fix race condition" @senior-dev` |
| `decision add` | `T004 decision by user: "Use Redis for caching?"` |

For `ticket update`, all changes are combined into a single log line. Order: status transition first (if present), then tokens, then artifacts.

### Manual `log` Command

```
split-board log --message "T003 dispatching to senior-dev agent" [--spec S001]
```

Same `append_log` helper, same format. The orchestrator uses this for events the CLI can't infer — dispatches, errors, free-form notes. Requires `--message`.

### CLI Changes

- `board.py`: Add `append_log(spec_dir, message)` function.
- `commands.py`: Each `cmd_*` function calls `append_log` after its mutation succeeds. For `spec init`, the log entry is the first line written to the new `log.md`.
- `cli.py`: Add `log` subcommand with `--message` (required) and `--spec` (optional, same resolution as other commands).
- `commands.py`: Add `cmd_log` handler that resolves the spec dir and calls `append_log`.

### Read-Only Commands

`status`, `validate`, `dashboard`, and `spec list` do not log. They don't mutate state.

## Scope Change to Existing Spec

The CLI design spec (`docs/superpowers/specs/2026-04-11-split-board-cli-design.md`) line 408 currently says:

> Append to `log.md` (that's the orchestrator skill, append-only text)

This changes to: the CLI owns logging. The orchestrator skill's step 7 ("Append to execution log") becomes automatic for mutations and uses `split-board log --message "..."` for everything else.

## Testing

- Every command's test asserts that `log.md` contains the expected entry after the command runs.
- Test the `log` command writes the exact message passed.
- Test that `log.md` accumulates entries (multiple commands → multiple lines).
- Test that read-only commands (`status`, `validate`) do not append to `log.md`.
