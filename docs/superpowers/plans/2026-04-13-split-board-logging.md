# Split Board CLI Logging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add automatic execution logging to every CLI mutation and a manual `log` command for orchestrator events.

**Architecture:** A single `append_log(spec_dir, message)` helper in `board.py` that every command handler calls after a successful mutation. A new `split-board log` subcommand for free-form entries.

**Tech Stack:** Python, PyYAML (existing deps only)

---

## File Structure

| File | Change | Responsibility |
|---|---|---|
| `split/tools/split_board/board.py` | Modify | Add `append_log` helper |
| `split/tools/split_board/commands.py` | Modify | Call `append_log` in every mutating `cmd_*` handler, add `cmd_log` |
| `split/tools/split_board/cli.py` | Modify | Add `log` subcommand parser |
| `tests/test_split_board.py` | Modify | Add logging assertions to existing tests, add new log-specific tests |

---

### Task 1: Add `append_log` helper to `board.py`

**Files:**
- Modify: `split/tools/split_board/board.py:48-50` (after `now_iso`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_split_board.py`:

```python
from split_board.board import append_log

def test_append_log_creates_entry(tmp_path):
    log_path = tmp_path / "log.md"
    log_path.write_text("")
    append_log(tmp_path, "T001 backlog→in_progress @dev")
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 1
    # ISO timestamp + space + message
    assert lines[0].endswith("T001 backlog→in_progress @dev")
    assert "T" in lines[0][:30]  # has ISO timestamp prefix


def test_append_log_accumulates(tmp_path):
    log_path = tmp_path / "log.md"
    log_path.write_text("")
    append_log(tmp_path, "first")
    append_log(tmp_path, "second")
    lines = log_path.read_text().strip().splitlines()
    assert len(lines) == 2
    assert lines[0].endswith("first")
    assert lines[1].endswith("second")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_append_log_creates_entry -v`
Expected: FAIL — `ImportError: cannot import name 'append_log'`

- [ ] **Step 3: Write minimal implementation**

Add to `split/tools/split_board/board.py` after the `now_iso()` function (after line 50):

```python
def append_log(spec_dir: Path, message: str) -> None:
    log_path = spec_dir / "log.md"
    with open(log_path, "a") as f:
        f.write(f"{now_iso()} {message}\n")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_append_log_creates_entry ../../tests/test_split_board.py::test_append_log_accumulates -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/board.py tests/test_split_board.py
git commit -m "Add append_log helper to board.py"
```

---

### Task 2: Add logging to `spec init`

**Files:**
- Modify: `split/tools/split_board/commands.py:38-63` (`cmd_spec_init`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_split_board.py`:

```python
def test_spec_init_logs(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Rate limiting"])
    spec_dir = list((tmp_path / "active").iterdir())[0]
    log = (spec_dir / "log.md").read_text().strip()
    assert 'S001 created: "Rate limiting"' in log
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_spec_init_logs -v`
Expected: FAIL — log.md is empty

- [ ] **Step 3: Implement**

In `split/tools/split_board/commands.py`, add `append_log` to the import from `.board`:

```python
from .board import (
    VALID_TRANSITIONS,
    append_log,
    error,
    ...
)
```

Then in `cmd_spec_init`, replace the line `(spec_dir / "log.md").write_text("")` and add the log call after `save_board`:

```python
    (spec_dir / "log.md").write_text("")
    ...
    save_board(board, spec_dir / "board.yaml")
    append_log(spec_dir, f'{spec_id} created: "{args.title}"')
    success(f"Spec {spec_id} created at {spec_dir}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_spec_init_logs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log spec init events"
```

---

### Task 3: Add logging to `spec archive` and `spec abandon`

**Files:**
- Modify: `split/tools/split_board/commands.py:98-111` (`_move_spec`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_split_board.py`:

```python
def test_spec_archive_logs(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "To archive"])
    main(["--base-dir", str(tmp_path), "spec", "archive", "--spec", "S001"])
    archived_dir = tmp_path / "archive" / "S001-to-archive"
    log = (archived_dir / "log.md").read_text().strip()
    assert "S001 archived" in log


def test_spec_abandon_logs(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "To abandon"])
    main(["--base-dir", str(tmp_path), "spec", "abandon", "--spec", "S001"])
    archived_dir = tmp_path / "archive" / "S001-to-abandon"
    log = (archived_dir / "log.md").read_text().strip()
    assert "S001 abandoned" in log
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_spec_archive_logs ../../tests/test_split_board.py::test_spec_abandon_logs -v`
Expected: FAIL — log entries not found

- [ ] **Step 3: Implement**

In `_move_spec` in `commands.py`, add the log call before moving the directory (since `spec_dir` won't exist after `shutil.move`):

```python
def _move_spec(args: argparse.Namespace, new_status: str) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, args.spec)
    archive_dir = base_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    board_path = spec_dir / "board.yaml"
    board = load_board(board_path)
    board["status"] = new_status
    save_board(board, board_path)

    append_log(spec_dir, f"{board.get('spec', spec_dir.name)} {new_status}")

    dest = archive_dir / spec_dir.name
    shutil.move(str(spec_dir), str(dest))
    success(f"Spec {board.get('spec', spec_dir.name)} {new_status} → {dest}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_spec_archive_logs ../../tests/test_split_board.py::test_spec_abandon_logs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log spec archive and abandon events"
```

---

### Task 4: Add logging to `milestone add` and `milestone move-ticket`

**Files:**
- Modify: `split/tools/split_board/commands.py:116-163` (`cmd_milestone_add`, `cmd_milestone_move_ticket`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_split_board.py`:

```python
def test_milestone_add_logs(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "milestone", "add", "--title", "Foundation"])
    log = (spec_dir / "log.md").read_text().strip()
    assert 'M001 added: "Foundation"' in log


def test_milestone_move_ticket_logs(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "milestone", "add", "--title", "M1"])
    main(["--base-dir", str(base), "milestone", "add", "--title", "M2"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "T", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "milestone", "move-ticket", "--ticket", "T001", "--milestone", "M002"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T001 moved to M002" in log
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_milestone_add_logs ../../tests/test_split_board.py::test_milestone_move_ticket_logs -v`
Expected: FAIL — log entries not found

- [ ] **Step 3: Implement**

In `cmd_milestone_add`, add after `save_board`:

```python
    save_board(board, board_path)
    append_log(spec_dir, f'{ms_id} added: "{args.title}"')
    success(f"Milestone {ms_id} added to {board['spec']}")
```

In `cmd_milestone_move_ticket`, add after `save_board`:

```python
    save_board(board, board_path)
    append_log(spec_dir, f"{args.ticket} moved to {args.milestone}")
    success(f"Ticket {args.ticket} moved to milestone {args.milestone}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_milestone_add_logs ../../tests/test_split_board.py::test_milestone_move_ticket_logs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log milestone add and move-ticket events"
```

---

### Task 5: Add logging to `ticket add`

**Files:**
- Modify: `split/tools/split_board/commands.py:168-218` (`cmd_ticket_add`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_split_board.py`:

```python
def test_ticket_add_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Do thing", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    log = (spec_dir / "log.md").read_text().strip()
    assert 'T001 added to M001: "Do thing" @dev' in log
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_ticket_add_logs -v`
Expected: FAIL — log entry not found

- [ ] **Step 3: Implement**

In `cmd_ticket_add`, add after `save_board`:

```python
    save_board(board, board_path)
    append_log(spec_dir, f'{ticket_id} added to {args.milestone}: "{args.title}" @{args.persona}')
    success(f"Ticket {ticket_id} added to {board['spec']} (milestone {args.milestone})")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_ticket_add_logs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log ticket add events"
```

---

### Task 6: Add logging to `ticket update`

This is the most complex handler — status, tokens, artifacts, and persona can all change in one call. All changes combine into one log line.

**Files:**
- Modify: `split/tools/split_board/commands.py:221-294` (`cmd_ticket_update`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_split_board.py`:

```python
def test_ticket_update_status_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T001 backlog→in_progress @dev" in log


def test_ticket_update_done_combined_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "done", "--tokens-used", "5000", "--artifact", "out.md"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T001 in_progress→done tokens=5000 artifact: out.md" in log


def test_ticket_update_tokens_only_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--tokens-used", "3000"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T001 tokens=3000" in log


def test_ticket_update_artifact_only_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--status", "in_progress"])
    main(["--base-dir", str(base), "ticket", "update", "--id", "T001", "--artifact", "out.md"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T001 artifact: out.md" in log
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py -k "test_ticket_update" -k "logs" -v`
Expected: FAIL — log entries not found

- [ ] **Step 3: Implement**

In `cmd_ticket_update`, build the log message from all changes and call `append_log` before the `success()` call. Replace the end of the function (after the persona update, before `recompute_ticket_blocked_statuses`):

```python
    if args.persona:
        ticket["persona"] = args.persona

    # Build log message from all changes
    parts = [args.id]
    if args.status:
        parts.append(f"{old_status}→{new_status} @{ticket['persona']}")
    if args.tokens_used is not None:
        parts.append(f"tokens={args.tokens_used}")
    if args.artifacts:
        for a in args.artifacts:
            parts.append(f"artifact: {a}")

    recompute_ticket_blocked_statuses(board)
    recompute_milestone_statuses(board)
    save_board(board, board_path)
    if len(parts) > 1:
        append_log(spec_dir, " ".join(parts))
    success(f"Ticket {args.id} updated")
```

Note: `old_status` is already captured at the top of the status-change block. Move its assignment to before the transition validation so it's available at the end. The variable `old_status` is already set at line 236 in the `if args.status:` block. We need to initialize it before the block so it's accessible later:

```python
    old_status = ticket["status"]

    if args.status:
        new_status = args.status
        ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py -k "ticket_update" -k "logs" -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to verify no regressions**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py -v`
Expected: All existing tests still PASS

- [ ] **Step 6: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log ticket update events with combined messages"
```

---

### Task 7: Add logging to `ticket add-dependency` and `ticket remove-dependency`

**Files:**
- Modify: `split/tools/split_board/commands.py:297-342` (`cmd_ticket_add_dependency`, `cmd_ticket_remove_dependency`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_split_board.py`:

```python
def test_ticket_add_dependency_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add-dependency", "--id", "T002", "--depends-on", "T001"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T002 dependency added: T001" in log


def test_ticket_remove_dependency_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "ticket", "add", "--title", "B", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001", "--depends-on", "T001"])
    main(["--base-dir", str(base), "ticket", "remove-dependency", "--id", "T002", "--depends-on", "T001"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T002 dependency removed: T001" in log
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_ticket_add_dependency_logs ../../tests/test_split_board.py::test_ticket_remove_dependency_logs -v`
Expected: FAIL — log entries not found

- [ ] **Step 3: Implement**

In `cmd_ticket_add_dependency`, add after `save_board`:

```python
    save_board(board, board_path)
    append_log(spec_dir, f"{args.id} dependency added: {args.depends_on}")
    success(f"Dependency {args.depends_on} added to {args.id}")
```

In `cmd_ticket_remove_dependency`, add after `save_board`:

```python
    save_board(board, board_path)
    append_log(spec_dir, f"{args.id} dependency removed: {args.depends_on}")
    success(f"Dependency {args.depends_on} removed from {args.id}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_ticket_add_dependency_logs ../../tests/test_split_board.py::test_ticket_remove_dependency_logs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log dependency add and remove events"
```

---

### Task 8: Add logging to `followup create`

**Files:**
- Modify: `split/tools/split_board/commands.py:347-392` (`cmd_followup_create`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_split_board.py`:

```python
def test_followup_create_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "Parent", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "followup", "create", "--parent", "T001", "--persona", "tester", "--title", "Fix race condition", "--acceptance-criteria", "ac", "--produces", "impl"])
    log = (spec_dir / "log.md").read_text().strip()
    assert 'T001a follow-up of T001: "Fix race condition" @tester' in log
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_followup_create_logs -v`
Expected: FAIL — log entry not found

- [ ] **Step 3: Implement**

In `cmd_followup_create`, add after `save_board`:

```python
    save_board(board, board_path)
    append_log(spec_dir, f'{followup_id} follow-up of {args.parent}: "{args.title}" @{args.persona}')
    success(f"Follow-up {followup_id} created for {args.parent}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_followup_create_logs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log followup create events"
```

---

### Task 9: Add logging to `decision add`

**Files:**
- Modify: `split/tools/split_board/commands.py:397-416` (`cmd_decision_add`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_split_board.py`:

```python
def test_decision_add_logs(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    main(["--base-dir", str(base), "decision", "add", "--ticket", "T001", "--question", "Redis or memory?", "--answered-by", "user", "--answer", "Redis"])
    log = (spec_dir / "log.md").read_text().strip()
    assert 'T001 decision by user: "Redis or memory?"' in log
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_decision_add_logs -v`
Expected: FAIL — log entry not found

- [ ] **Step 3: Implement**

In `cmd_decision_add`, add after `save_board`:

```python
    save_board(board, board_path)
    append_log(spec_dir, f'{args.ticket} decision by {args.answered_by}: "{args.question}"')
    success(f"Decision recorded on {args.ticket}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_decision_add_logs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Log decision add events"
```

---

### Task 10: Add `split-board log` subcommand

**Files:**
- Modify: `split/tools/split_board/cli.py:6-23` (imports), `cli.py:133-148` (parser)
- Modify: `split/tools/split_board/commands.py` (add `cmd_log`)
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_split_board.py`:

```python
def test_log_command(tmp_path):
    base, spec_dir = _init_spec(tmp_path)
    main(["--base-dir", str(base), "log", "--message", "T003 dispatching to senior-dev agent"])
    log = (spec_dir / "log.md").read_text().strip()
    assert "T003 dispatching to senior-dev agent" in log


def test_log_command_with_spec(tmp_path):
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Alpha"])
    main(["--base-dir", str(tmp_path), "spec", "init", "--title", "Beta"])
    main(["--base-dir", str(tmp_path), "log", "--message", "hello from S002", "--spec", "S002"])
    spec_dir = tmp_path / "active" / "S002-beta"
    log = (spec_dir / "log.md").read_text().strip()
    assert "hello from S002" in log
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_log_command ../../tests/test_split_board.py::test_log_command_with_spec -v`
Expected: FAIL — `error: argument command: invalid choice: 'log'`

- [ ] **Step 3: Implement the command handler**

Add to `split/tools/split_board/commands.py`:

```python
# --- Log ---

def cmd_log(args: argparse.Namespace) -> None:
    base_dir = Path(args.base_dir)
    spec_dir = resolve_spec_dir(base_dir, getattr(args, "spec", None))
    append_log(spec_dir, args.message)
    success(f"Logged: {args.message}")
```

- [ ] **Step 4: Wire up the CLI parser**

In `split/tools/split_board/cli.py`, add `cmd_log` to the import:

```python
from .commands import (
    cmd_dashboard,
    cmd_decision_add,
    cmd_followup_create,
    cmd_log,
    cmd_milestone_add,
    ...
)
```

Add the subparser after the `decision` block and before `dashboard`:

```python
    # log
    log_p = sub.add_parser("log", help="Append a message to the execution log")
    log_p.add_argument("--message", required=True, help="Message to log")
    log_p.add_argument("--spec")
    log_p.set_defaults(func=cmd_log)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_log_command ../../tests/test_split_board.py::test_log_command_with_spec -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add split/tools/split_board/cli.py split/tools/split_board/commands.py tests/test_split_board.py
git commit -m "Add split-board log subcommand"
```

---

### Task 11: Add test for read-only commands not logging

**Files:**
- Test: `tests/test_split_board.py`

- [ ] **Step 1: Write the test**

Add to `tests/test_split_board.py`:

```python
def test_readonly_commands_do_not_log(tmp_path):
    base, spec_dir = _init_spec_with_milestone(tmp_path)
    main(["--base-dir", str(base), "ticket", "add", "--title", "A", "--persona", "dev", "--acceptance-criteria", "ac", "--produces", "impl", "--milestone", "M001"])
    log_before = (spec_dir / "log.md").read_text()
    main(["--base-dir", str(base), "status"])
    main(["--base-dir", str(base), "validate"])
    log_after = (spec_dir / "log.md").read_text()
    assert log_before == log_after
```

- [ ] **Step 2: Run test to verify it passes**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py::test_readonly_commands_do_not_log -v`
Expected: PASS (read-only commands never call `append_log`)

- [ ] **Step 3: Run full test suite**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py -v`
Expected: All tests PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_split_board.py
git commit -m "Add test confirming read-only commands do not log"
```

---

### Task 12: Run full suite and final commit

- [ ] **Step 1: Run full test suite**

Run: `cd split/tools && python -m pytest ../../tests/test_split_board.py -v`
Expected: All tests PASS

- [ ] **Step 2: Verify log output manually**

Run: `cd split/tools && python -m split_board --base-dir /tmp/test-log spec init --title "Log test" && python -m split_board --base-dir /tmp/test-log milestone add --title "M1" && python -m split_board --base-dir /tmp/test-log ticket add --title "Do thing" --persona dev --acceptance-criteria ac --produces impl --milestone M001 && python -m split_board --base-dir /tmp/test-log log --message "T001 dispatching to dev agent" && cat /tmp/test-log/active/S001-log-test/log.md`

Expected: 4 timestamped lines in log.md
