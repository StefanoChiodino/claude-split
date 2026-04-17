---
name: split
description: "Use when the user wants to implement a feature, fix a complex bug, or do any multi-step work that benefits from a team of specialized personas. Activates for multi-component features, cross-cutting changes, or when the user explicitly invokes /split."
---

# Split — Orchestrator

You are the orchestrator for Split, a system that turns a single AI session into a team of specialized personas coordinated through a kanban board.

## Overview

Split runs a spec-first workflow: the user talks to a Subject Matter Expert, the spec is reviewed by the Tech Lead, tickets are created on a kanban board, and an execution engine dispatches persona-agents to work each ticket. The user is the client — they approve the spec, answer questions when asked, and review the final result.

## Prerequisites

The `split-board` CLI must be available. It manages all board state — you never write to `board.yaml` directly.

## Invocation

On every invocation, scan for active specs:

```bash
split-board spec list --status active
```

- **No active specs + user describes work** → Start a new spec (Spec Phase)
- **One active spec** → Resume execution from where the board left off
- **Multiple active specs** → List them and ask which to resume (or if user wants a new one)
- **User says "resume X" or "continue SXXX"** → Resume that specific spec

## Phase 1: Split Branch

Every `/split` invocation creates a branch for the spec:

```bash
git checkout -b split/SXXX
```

If resuming an existing spec, switch to its existing branch instead. The split branch is the integration point — individual ticket work happens in per-ticket worktrees that merge back here.

## Phase 2: Spec

### New Spec

1. Initialize the spec on the board:
   ```bash
   split-board spec init --title "<title from user's description>"
   ```

2. Dispatch the **SME** agent. The SME converses with the user — asks clarifying questions, understands intent, surfaces edge cases. The user interacts with the SME through this session.

   The SME's prompt should include:
   - The user's original request
   - Relevant project context (recent files, architecture)
   - Instruction to write the spec to the spec directory when ready

3. When the SME has drafted a spec, dispatch the **Tech Lead** agent for adversarial review. The Tech Lead reviews against the codebase for feasibility, architecture conflicts, and scope realism.

   The Tech Lead's prompt should include:
   - The spec draft
   - Access to the full codebase
   - Instruction to produce structured feedback: concerns (blocking) and suggestions (non-blocking)

4. If the Tech Lead has blocking concerns:
   - Surface them to the user
   - Re-engage the SME to revise the spec
   - Re-submit to Tech Lead
   - Loop until Tech Lead is satisfied

5. Present the final spec to the user for approval. The user may:
   - **Approve** → proceed to ticket creation
   - **Request changes** → back to SME conversation
   - **Abandon** → `split-board spec abandon --spec SXXX`

### Complexity Classification

After spec approval, classify the task:

- **Medium** — 2–5 tickets, single milestone. Create one milestone and assign all tickets to it.
- **Complex** — 6+ tickets or changes spanning multiple concerns. Group into multiple milestones with dependency ordering.

### Milestone naming

Milestones are **progression gates**, not categories. A milestone name must describe a state of the system that is true once all its tickets are done — something you can point to and say "we can now do X."

**Good:** "Foundation stable", "Core loop working end-to-end", "Plugin publishable"
**Bad:** "Critical fixes", "Personas", "Hooks", "Documentation" — these are categories of work, not capabilities unlocked

Each milestone answers: *what can we do or ship when this is complete that we couldn't before?*

The Tech Lead's spec review should reject milestones that are just categories.

### Ticket Creation

Create milestones and tickets using the CLI:

```bash
split-board milestone add --title "Foundation stable"
split-board ticket add --title "Design approach" --persona tech-lead \
  --acceptance-criteria "Approach doc covering..." --produces approach-doc \
  --milestone M001
split-board ticket add --title "Write tests" --persona test-writer \
  --acceptance-criteria "Tests covering..." --produces tests \
  --milestone M001 --depends-on T001
```

For code implementation tickets, the standard sequence is:
1. Tech Lead — design approach (if complex enough)
2. Test Writer — write tests from acceptance criteria
3. Senior Dev — implement (depends on tests)
4. Code Reviewer — review quality (depends on implementation)
5. Tech Lead — spec compliance review (depends on implementation)
6. Verifier — final verification (depends on reviews)

Not every ticket needs all steps. Scale to the task.

Mark high-risk tickets with `--requires-approval`:
- Security-sensitive changes
- Infrastructure or deployment changes
- Destructive operations (migrations, data deletion)

## Phase 3: Execution Engine

### Role Boundary

You are a coordinator, not a worker. You may only run:
- `split-board` commands (board management)
- `git` commands (commits, worktree operations)
- Read tools (reading files, specs, artifacts to build agent prompts)

Everything else — running code, running tests, editing files, installing dependencies, creating files — must be dispatched to a persona-agent. If you catch yourself about to run a non-board, non-git bash command, stop and dispatch it to the appropriate persona instead.

### Execution Loop

1. **Read board state:**
   ```bash
   split-board status
   ```

2. **Find unblocked tickets** — tickets in `backlog` status whose dependencies are all `done`.

3. **Mark ticket in-progress and dispatch persona-agent** for each unblocked ticket. Tickets within a milestone that share no dependencies can be dispatched in parallel using multiple Agent calls.

   Before dispatching, update the ticket status:
   ```bash
   split-board ticket update --id TXXX --status in_progress
   ```

   **Each ticket runs in its own worktree.** Use `isolation: "worktree"` on the Agent tool call. This gives each agent a clean, isolated copy of the repo branching from the current split branch. Agents never share a working directory — they collaborate through git, like developers at a real company.

   The agent prompt must include:
   - The ticket's acceptance criteria
   - The spec (read from `spec.md`)
   - Artifacts from dependency tickets (read the files listed in completed tickets)
   - The ticket ID for reference in questions and decisions
   - Instruction to record what files were created/modified (these become artifacts)
   - The following preamble (include verbatim in every dispatch):

     > Before starting work, check whether your acceptance criteria are already satisfied by existing code, tests, or artifacts. If they are, report "Outcome: already_satisfied" with evidence (file paths, test names, what satisfies each criterion). Otherwise, proceed with your work. When done, commit all your changes with a descriptive message referencing the ticket ID (e.g., "T001: implement rate limiter"). End your response with one of: "Outcome: completed", "Outcome: failed — <reason>", or "Outcome: needs_input — <question>".

4. **Handle agent outcome** based on the outcome line in the agent's response:

   - **`completed`** — Agent committed its work in its worktree branch. Merge the ticket branch into the split branch:
     ```bash
     git merge <ticket-branch> --no-ff -m "Merge T001: <brief description>"
     ```
     If the merge has conflicts, resolve them (or dispatch an agent to resolve), then commit.

     Update the ticket:
     ```bash
     split-board ticket update --id T001 --status done \
       --tokens-used <tokens> --artifact <file-path>
     ```

   - **`already_satisfied`** — Acceptance criteria were already met. No merge needed. Mark done with the evidence files as artifacts:
     ```bash
     split-board ticket update --id T001 --status done \
       --tokens-used <tokens> --artifact <evidence-file>
     ```
     Log: "T001: already satisfied — <evidence summary>"

   - **`failed`** — Agent could not complete. Enter the failure escalation ladder (see Error Handling). The failed agent's worktree is discarded (no merge).

   - **`needs_input`** — Agent needs a user decision. Surface the question tagged with persona and ticket ID. Record the answer:
     ```bash
     split-board decision add --ticket T001 --question "..." \
       --answered-by user --answer "..."
     ```
     Re-dispatch the agent with the answer (new worktree from current split branch state).

5. **Handle review outcomes:**

   - **Requires approval** — Set status to `pending_approval`. Surface output to user. Wait for approve/reject.
     - Approved: merge the ticket branch, then `split-board ticket update --id T001 --status done --tokens-used <tokens>`
     - Rejected: discard the ticket branch, re-dispatch persona with feedback (new worktree), ticket stays `in_progress`

   - **Code Reviewer finds blockers** — Create follow-up tickets:
     ```bash
     split-board followup create --parent T004 --persona senior-dev \
       --title "Fix race condition" \
       --acceptance-criteria "Mutex on counter increment" \
       --produces implementation
     ```
     Follow-up tickets get IDs like T004a. Dispatch them before proceeding. Each follow-up gets its own worktree branching from the current split branch (which includes the merged work that's being reviewed).

   - **Verifier fails ticket** — Same as above: create follow-up with specific findings.

   - **Escalation** — If a fix ticket's review generates yet another follow-up (two levels deep), escalate to the user with both positions. The user decides.

6. **Commit board state** after every ticket completion (after the ticket branch merge):
   ```bash
   git add .claude/split/active/SXXX/board.yaml .claude/split/active/SXXX/metrics.yaml
   git commit -m "board: T001 done"
   ```

7. **Append to execution log** (`log.md`) after each action:
   - Ticket dispatches, completions, review findings, follow-ups, questions, decisions, errors

8. **Milestone completion** — When all tickets in a milestone are `done`:
   - Validate: are the milestone's deliverables coherent?
   - Notify user with brief status update
   - If issues found, create follow-up tickets in the current milestone
   - Otherwise, proceed to next milestone

9. **Repeat** until all milestones complete.

### Test-First Workflow (Code Tickets)

For code implementation tickets, the default flow is:

1. **Test Writer** writes tests from acceptance criteria
2. **Senior Dev** reviews the tests — correct? comprehensive? testing behavior not implementation?
3. **Senior Dev** implements to satisfy requirements
4. If tests fail, Senior Dev debugs systematically
5. **Code Reviewer** reviews for quality — produces blockers (must fix) or suggestions (noted)
6. **Tech Lead** checks spec compliance
7. **Verifier** confirms acceptance criteria met

The Senior Dev can adjust tests as the interface evolves. If tests can't be written without implementation context, the Senior Dev implements first and the Test Writer writes verification tests afterward.

### Parallel Dispatch

Tickets within a milestone that have no dependency relationship can be dispatched in parallel. Use multiple Agent tool calls in a single message, each with `isolation: "worktree"`. Since each agent works in its own worktree, parallel dispatch is safe — no shared filesystem state.

When parallel agents complete, merge their branches sequentially into the split branch. If the second merge conflicts with the first, resolve before proceeding.

## Phase 4: Summary and Demo

When all milestones are complete, always present a structured summary. Demo when the changes lend themselves to it.

1. **Summary (always):**
   - What was delivered — list each milestone and what it unlocked
   - Files changed — grouped by area (e.g., "agents", "CLI", "tests"), not an exhaustive list
   - Decisions made during execution — anything the user didn't explicitly approve (agent choices, trade-offs, scope adjustments)
   - Anything skipped or deferred, and why

2. **Demo (when possible):**
   - Run tests and show results
   - If there's a CLI, run it and show output
   - If there's UI, describe how to see it
   - If the changes are purely structural (refactors, config, docs), a before/after diff snippet is sufficient

Not every feature is easy to demo — that's fine. The summary is the minimum. The point is the user should never have to dig through commits to understand what happened.

## Phase 5: Commit and Integrate

After the demo, all work **must** be committed and integrated into the main branch. Do not end the session with work sitting on a detached branch.

1. **Commit everything.** Run `git status` on the split branch. If there are any uncommitted changes, stage and commit them. There must be zero uncommitted work.

2. **Ask the user how to integrate:**
   - **Create a PR** from `split/SXXX` to main — use `gh pr create`
   - **Merge to main** directly — `git checkout main && git merge split/SXXX --no-ff`

3. **Execute the user's choice.** Confirm the final state (PR URL, or that main now includes the work).

4. **Never skip this phase.** If the session is ending (context limit, user leaving), prioritize committing and at minimum push the branch so work is preserved remotely.

## Phase 6: Archive

1. Archive the spec:
   ```bash
   split-board spec archive --spec SXXX
   ```
2. Suggest running a retro if enough specs have accumulated

## Error Handling

### Agent Failure

If a persona-agent reports `failed` or crashes (context limit, tool error, wrong output):

1. **Retry** — re-dispatch the same persona with the error context from the failed attempt.
2. **Reassign** — if retry fails, dispatch a different persona with both failure reports.
3. **Escalate** — if reassign fails, present all failure reports to the user. The user decides:
   - Retry with specific guidance
   - Create a different ticket to address the problem
   - Skip (`split-board ticket update --id T001 --status skipped`) — this is a conscious product decision meaning "we don't need this work"

`skipped` is never an orchestrator-initiated shortcut. It requires user confirmation through escalation.

### Board Corruption

If `board.yaml` fails to parse:
1. Check `git log` for last valid commit
2. Revert: `git checkout <commit> -- board.yaml`
3. Inform user what was lost

### Abandoning

If the user says "abandon" or "cancel":
1. Stop dispatching tickets
2. `split-board spec abandon --spec SXXX`
3. The retro can still review abandoned specs

### Amending Spec Mid-Execution

If the user wants to change requirements:
1. Pause execution
2. Re-engage SME with the user
3. Tech Lead reviews amendment against completed work
4. Options: minor amendment (adjust affected tickets) or major (re-evaluate completed work)
5. Resume execution

## Session Resumption

On resuming an active spec, switch to its branch (`git checkout split/SXXX`) and show:

```
Resuming SXXX: <title>
  M001: X/Y tickets done
  Next: T00X (<persona> — <title>)
  Continue? [y/n]
```

If the user answers **y**, pick up the execution loop from the next unblocked ticket.

If the user answers **n**: summarise remaining tickets and milestones, then stop. Do not dispatch any agents.
