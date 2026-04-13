# Split: Structured Agent Outcomes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured agent outcome reporting to the split orchestrator, replace skip-on-failure with an escalation ladder, and fix milestone completion to count `skipped` as resolved.

**Architecture:** Three changes — orchestrator skill text (agent prompt preamble + outcome handling + escalation ladder), and two Python one-liners (milestone + metrics). The Python changes are identical: `== "done"` becomes `in ("done", "skipped")`.

**Tech Stack:** Python (split-board CLI), Markdown (orchestrator skill)

---

### Task 1: Test milestone completion counts skipped as resolved

**Files:**
- Modify: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add after the existing `test_milestone_status_auto_computed` test:

```python
def test_milestone_done_when_all_done_or_skipped(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "milestone", "add", "--title", "M1"])
    main(["--base-dir", str(base), "milestone", "add", "--title", "M2"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "Impl", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "Tests", "--persona", "test-writer", "--acceptance-criteria", "ac", "--produces", "tests", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "Other", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M002"])
    # Complete T001, skip T002
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done", "--tokens-used", "100", "--artifact", "a.py"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T002", "--status", "skipped"])
    board = _load(spec_dir)
    assert board["milestones"][0]["status"] == "done"
    assert board["milestones"][1]["status"] == "in_progress"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_split_board.py::test_milestone_done_when_all_done_or_skipped -v`

Expected: FAIL — milestone status is `in_progress` because `skipped != done`

### Task 2: Test metrics counts milestone with skipped tickets as completed

**Files:**
- Modify: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add after the existing `test_metrics_through_full_workflow` test:

```python
def test_metrics_counts_skipped_milestone_as_completed(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Impl", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "Tests", "--persona", "test-writer", "--acceptance-criteria", "ac", "--produces", "tests", "--milestone", "M001"])
    # Complete T001, skip T002
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done", "--tokens-used", "100", "--artifact", "a.py"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T002", "--status", "skipped"])
    metrics = _metrics(spec_dir)
    assert metrics["milestones_completed"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_split_board.py::test_metrics_counts_skipped_milestone_as_completed -v`

Expected: FAIL — `milestones_completed` is `0` because skipped tickets aren't counted

### Task 3: Fix milestone completion to count skipped as resolved

**Files:**
- Modify: `src/split_board/validation.py:74`

- [ ] **Step 1: Update recompute_milestone_statuses**

In `src/split_board/validation.py`, change line 74 from:

```python
        all_done = ms_tickets and all(t.get("status") == "done" for t in ms_tickets)
```

to:

```python
        all_done = ms_tickets and all(t.get("status") in ("done", "skipped") for t in ms_tickets)
```

- [ ] **Step 2: Run milestone test to verify it passes**

Run: `python -m pytest tests/test_split_board.py::test_milestone_done_when_all_done_or_skipped -v`

Expected: PASS

### Task 4: Fix metrics to count skipped milestone as completed

**Files:**
- Modify: `src/split_board/board.py:116`

- [ ] **Step 1: Update compute_metrics**

In `src/split_board/board.py`, change line 116 from:

```python
        if ms_tickets and all(t.get("status") == "done" for t in ms_tickets):
```

to:

```python
        if ms_tickets and all(t.get("status") in ("done", "skipped") for t in ms_tickets):
```

- [ ] **Step 2: Run metrics test to verify it passes**

Run: `python -m pytest tests/test_split_board.py::test_metrics_counts_skipped_milestone_as_completed -v`

Expected: PASS

- [ ] **Step 3: Run full test suite**

Run: `python -m pytest tests/test_split_board.py -v`

Expected: All tests pass (existing tests unaffected)

- [ ] **Step 4: Commit**

```bash
git add src/split_board/validation.py src/split_board/board.py tests/test_split_board.py
git commit -m "fix: count skipped tickets as resolved for milestone completion"
```

### Task 5: Add agent outcome handling to orchestrator execution loop

**Files:**
- Modify: `split/skills/split/SKILL.md:131-169`

- [ ] **Step 1: Add agent prompt preamble to dispatch instructions**

In `split/skills/split/SKILL.md`, replace lines 131-138 (the dispatch step and its prompt requirements):

```markdown
3. **Dispatch persona-agent** for each unblocked ticket. Tickets within a milestone that share no dependencies can be dispatched in parallel using multiple Agent calls.

   The agent prompt must include:
   - The ticket's acceptance criteria
   - The spec (read from `spec.md`)
   - Artifacts from dependency tickets (read the files listed in completed tickets)
   - The ticket ID for reference in questions and decisions
   - Instruction to record what files were created/modified (these become artifacts)
```

with:

```markdown
3. **Dispatch persona-agent** for each unblocked ticket. Tickets within a milestone that share no dependencies can be dispatched in parallel using multiple Agent calls.

   The agent prompt must include:
   - The ticket's acceptance criteria
   - The spec (read from `spec.md`)
   - Artifacts from dependency tickets (read the files listed in completed tickets)
   - The ticket ID for reference in questions and decisions
   - Instruction to record what files were created/modified (these become artifacts)
   - The following preamble (include verbatim in every dispatch):

     > Before starting work, check whether your acceptance criteria are already satisfied by existing code, tests, or artifacts. If they are, report "Outcome: already_satisfied" with evidence (file paths, test names, what satisfies each criterion). Otherwise, proceed with your work and end your response with one of: "Outcome: completed", "Outcome: failed — <reason>", or "Outcome: needs_input — <question>".
```

- [ ] **Step 2: Replace the ticket update step and special outcomes with outcome handling**

Replace lines 140-169 (steps 4 and 5):

```markdown
4. **Update the ticket** when the agent completes:
   ```bash
   split-board ticket update --id T001 --status done \
     --tokens-used <tokens> --artifact <file-path>
   ```

5. **Handle special outcomes:**

   - **Persona has questions** — Surface to the user tagged with persona and ticket ID. Record answers as decisions:
     ```bash
     split-board decision add --ticket T001 --question "..." \
       --answered-by user --answer "..."
     ```

   - **Requires approval** — Set status to `pending_approval`. Surface output to user. Wait for approve/reject.
     - Approved: `split-board ticket update --id T001 --status done`
     - Rejected: re-dispatch persona with feedback, ticket stays `in_progress`

   - **Code Reviewer finds blockers** — Create follow-up tickets:
     ```bash
     split-board followup create --parent T004 --persona senior-dev \
       --title "Fix race condition" \
       --acceptance-criteria "Mutex on counter increment" \
       --produces implementation
     ```
     Follow-up tickets get IDs like T004a. Dispatch them before proceeding.

   - **Verifier fails ticket** — Same as above: create follow-up with specific findings.

   - **Escalation** — If a fix ticket's review generates yet another follow-up (two levels deep), escalate to the user with both positions. The user decides.
```

with:

```markdown
4. **Handle agent outcome** based on the outcome line in the agent's response:

   - **`completed`** — Agent did the work. Update the ticket:
     ```bash
     split-board ticket update --id T001 --status done \
       --tokens-used <tokens> --artifact <file-path>
     ```

   - **`already_satisfied`** — Acceptance criteria were already met. Mark done with the evidence files as artifacts:
     ```bash
     split-board ticket update --id T001 --status done \
       --tokens-used <tokens> --artifact <evidence-file>
     ```
     Log: "T001: already satisfied — <evidence summary>"

   - **`failed`** — Agent could not complete. Enter the failure escalation ladder (see Error Handling).

   - **`needs_input`** — Agent needs a user decision. Surface the question tagged with persona and ticket ID. Record the answer:
     ```bash
     split-board decision add --ticket T001 --question "..." \
       --answered-by user --answer "..."
     ```
     Re-dispatch the agent with the answer.

5. **Handle review outcomes:**

   - **Requires approval** — Set status to `pending_approval`. Surface output to user. Wait for approve/reject.
     - Approved: `split-board ticket update --id T001 --status done`
     - Rejected: re-dispatch persona with feedback, ticket stays `in_progress`

   - **Code Reviewer finds blockers** — Create follow-up tickets:
     ```bash
     split-board followup create --parent T004 --persona senior-dev \
       --title "Fix race condition" \
       --acceptance-criteria "Mutex on counter increment" \
       --produces implementation
     ```
     Follow-up tickets get IDs like T004a. Dispatch them before proceeding.

   - **Verifier fails ticket** — Same as above: create follow-up with specific findings.

   - **Escalation** — If a fix ticket's review generates yet another follow-up (two levels deep), escalate to the user with both positions. The user decides.
```

### Task 6: Replace error handling with escalation ladder

**Files:**
- Modify: `split/skills/split/SKILL.md:233-241`

- [ ] **Step 1: Replace Agent Failure section**

Replace lines 235-241:

```markdown
### Agent Failure

If a persona-agent fails (context limit, tool error, wrong output):

1. Report to user: "[Persona] failed on [ticket]: [reason]"
2. Offer: retry (re-dispatch with error context), reassign (different persona), or skip
3. If skipped: `split-board ticket update --id T001 --status skipped`
```

with:

```markdown
### Agent Failure

If a persona-agent reports `failed` or crashes (context limit, tool error, wrong output):

1. **Retry** — re-dispatch the same persona with the error context from the failed attempt.
2. **Reassign** — if retry fails, dispatch a different persona with both failure reports.
3. **Escalate** — if reassign fails, present all failure reports to the user. The user decides:
   - Retry with specific guidance
   - Create a different ticket to address the problem
   - Skip (`split-board ticket update --id T001 --status skipped`) — this is a conscious product decision meaning "we don't need this work"

`skipped` is never an orchestrator-initiated shortcut. It requires user confirmation through escalation.
```

- [ ] **Step 2: Commit**

```bash
git add split/skills/split/SKILL.md
git commit -m "feat: add structured agent outcomes and escalation ladder to orchestrator"
```

### Task 7: Run full test suite and verify

- [ ] **Step 1: Run all split-board tests**

Run: `python -m pytest tests/test_split_board.py -v`

Expected: All tests pass

- [ ] **Step 2: Verify SKILL.md is well-formed**

Read `split/skills/split/SKILL.md` end-to-end and confirm:
- The outcome preamble appears in the dispatch step
- The outcome handling replaces the old step 4/5
- The error handling section uses the escalation ladder
- No dangling references to the old "offer: retry, reassign, or skip" pattern
