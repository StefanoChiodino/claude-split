# Split: Structured Agent Outcomes and Milestone Completion

## Problem

The orchestrator has two gaps:

1. When a persona-agent is dispatched and discovers its acceptance criteria are already satisfied (e.g., tests written by a prior ticket), there is no path to mark the ticket `done`. The agent has nothing to do, the orchestrator treats this as a failure, and the ticket gets `skipped` — misrepresenting the situation.

2. `skipped` conflates two meanings: "product decision: not needed" and "failed and we moved on." Milestone completion cannot trust `skipped` as resolved because it might mask unfinished work.

## Design

### Structured Agent Outcomes

Every persona-agent reports a structured outcome. The orchestrator includes a standard preamble in every dispatch prompt (not in individual agent definitions):

> Before starting work, check whether your acceptance criteria are already satisfied by existing code/artifacts. If they are, report outcome `already_satisfied` with evidence (file paths, test names, etc.). Otherwise, proceed with your work and report one of the outcomes below when done.

Outcomes:

| Outcome | Meaning | Orchestrator action |
|---|---|---|
| `completed` | Agent did the work. Lists artifacts. | Mark `done`, record artifacts, commit. |
| `already_satisfied` | Acceptance criteria already met. Lists evidence. | Mark `done`, record evidence as artifacts, commit. Log: "T00X: already satisfied — <evidence summary>". |
| `failed` | Agent attempted but could not complete. States reason. | Enter failure escalation (see below). |
| `needs_input` | Agent needs a user decision before proceeding. | Surface question, record decision, re-dispatch. |

The outcome is communicated in the agent's final response as a clearly labelled line (e.g., "Outcome: completed", "Outcome: already_satisfied — tests exist in tests/test_model.py"). The orchestrator reads the agent's response and acts on the outcome line. No schema change to `board.yaml`.

### Failure Escalation (replaces current error handling)

Current behavior: on agent failure, offer retry/reassign/skip.

New behavior — escalation ladder, no early skip:

1. **Retry** — re-dispatch with error context from the failed attempt.
2. **Reassign** — dispatch a different persona with the failure report.
3. **Escalate to user** — present both failure reports. User decides:
   - Retry with specific guidance
   - Create a different ticket to address the problem
   - Skip (conscious product decision: "we don't need this")

`skip` is only reachable through user escalation. It is never an orchestrator-initiated shortcut.

### Milestone Completion

With `skipped` now reliably meaning "product decision: not needed," milestone completion counts it as resolved.

A milestone is `done` when every ticket has status `done` or `skipped`.

Changes:
- `src/split_board/validation.py` `recompute_milestone_statuses`: `all(status in ("done", "skipped"))` instead of `all(status == "done")`
- `src/split_board/board.py` `compute_metrics`: same change for `milestones_completed`

### Scope

| File | Change |
|---|---|
| `split/skills/split/SKILL.md` | Execution loop: add agent outcome handling after dispatch. Error handling: replace retry/reassign/skip with escalation ladder. Agent prompt: add standard preamble for outcome reporting. |
| `src/split_board/validation.py` | `recompute_milestone_statuses`: count `skipped` as resolved. |
| `src/split_board/board.py` | `compute_metrics`: count `skipped` as resolved. |

No changes to: agent definitions, CLI, board schema, dashboard, or valid transitions.
