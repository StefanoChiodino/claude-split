# Spec: Fix Plugin Review Findings

## Objective

Address the findings from the 2026-04-14 plugin review (52 findings across 7 sections) plus a newly discovered Critical worktree isolation bug. This work turns claude-split from "functional early release" into a reliable, correctly-isolated plugin that follows Claude Code conventions.

We focus on Critical, High, and correctness-affecting Medium findings. Low-severity polish items (colors, optional metadata, style consistency) are explicitly deferred.

## Scope

### Included

- **Critical (2):** `error()` / `sys.exit` refactor; worktree isolation bug
- **High (16):** All 16 High findings from the review
- **Medium (selected):** Findings that affect correctness, usability, or prevent silent data loss (12 of 22)

### Excluded (out of scope)

- **Low findings** -- agent colors, `pyproject.toml` optional deps for textual, `.venv` cache path, `plugin.json` repository field, `guard-board.sh` stdin JSON validation, empty `slugify` test, follow-up ID exhaustion test, fixture refactoring, inconsistent `pathlib` vs `os.listdir`, `async` field in hooks, Test Writer not running tests, Tech Lead spec review output format, context window exhaustion guidance
- **Model assignment (`model: sonnet` for simpler agents)** -- valid concern but involves cost/quality trade-offs the user should decide on separately
- **`install-cli.sh` rename to `setup-permissions.sh`** -- cosmetic, no functional impact

---

## Milestones

### M001: Critical -- worktree isolation and `error()` refactor

**Goal:** Fix the two Critical issues that undermine testability and isolation.

#### 1a. Worktree isolation (newly discovered Critical)

The SKILL.md orchestrator creates a git worktree but then gives agents absolute paths to the main repo. All file writes bypass isolation.

**Changes to `split/skills/split/SKILL.md`:**

- Replace the `EnterWorktree(name: "split-SXXX")` pseudo-code (line 36) with the real tool call syntax. `EnterWorktree` is an actual Claude Code tool (confirmed working). The correct invocation is:
  ```
  EnterWorktree(name: "split-SXXX")
  ```
  After this call, the session CWD changes to the worktree path (e.g. `.claude/worktrees/split-SXXX`). This addresses the review finding [Medium].

- Add an explicit instruction immediately after `EnterWorktree`: "After entering the worktree, capture the current working directory (`$PWD` or equivalent). All agent dispatch prompts MUST use this path — not the original repo root — for any file path references. Never hardcode the main repo path in agent prompts."

- Ensure the `split-board` CLI is invoked with paths relative to the worktree CWD, not the main repo. Since the orchestrator's CWD is now the worktree, relative paths naturally point to the right place.

- In Phase 3 step 6 (commit board state), git commands run inside the worktree CWD and therefore commit to the worktree branch, not master.

**Note:** The isolation bug in previous sessions (files written to main repo) was caused by agents receiving hardcoded absolute paths to the main repo in their prompts. The fix is a SKILL.md instruction discipline issue, not a code change.

#### 1b. `error()` refactor (Critical)

`board.py:error()` calls `sys.exit(1)`, making every error path untestable without `pytest.raises(SystemExit)` and making the module unsafe as a library.

**Changes to `split/tools/src/split_board/board.py`:**

- Define `class BoardError(Exception): pass` at module level.
- Change `error()` to raise `BoardError(msg)` instead of calling `sys.exit(1)`. Keep the `print(..., file=sys.stderr)` for message formatting, or move formatting into the exception's `__str__`.
- Annotate `error()` return type as `-> Never` (Python 3.11+ via `typing.Never`).

**Changes to `split/tools/src/split_board/cli.py`:**

- In `main()`, wrap `args.func(args)` in `try: ... except BoardError as e: print(f"ERROR: {e}", file=sys.stderr); sys.exit(1)`.

**Changes to `split/tools/src/split_board/commands.py`:**

- **`cmd_ticket_update` needs no restructuring.** Validation (lines 239-278) already completes before any mutations occur (first mutation at line 280). No validate-before-mutate problem exists.

- **`cmd_validate`** (line 512): keep its own `sys.exit(1)` — it is a top-level command that prints structured results and exits non-zero to signal failure. It does not use `error()` and does not need to change.

**Changes to `tests/test_split_board.py`:**

- Change all `pytest.raises(SystemExit)` to `pytest.raises(BoardError)`.
- Import `BoardError` from `split_board.board`.

**Also addressed:** [High] `next_followup_id` implicit `Never` return -- annotating `error()` as `-> Never` resolves the type-checker warning since `error()` is the only code path that doesn't return a `str`.

---

### M002: Persona fixes

**Goal:** Fix agent configurations that cause incorrect behavior, missing instructions, or invalid tool declarations.

#### 2a. Fix `@agents/shared/` import syntax (High)

Every agent file ends with `@agents/shared/core-operating-principle.md`. This `@path` import syntax is not supported in Claude Code plugin agents (GitHub issue #5914).

**Fix:** Inline the content of `core-operating-principle.md` directly into each of the 11 agent `.md` files, replacing the `@agents/shared/core-operating-principle.md` line. Keep `split/agents/shared/core-operating-principle.md` as the canonical source for human reference but do not rely on runtime import.

**Files changed:** All 11 agent files under `split/agents/`.

#### 2b. Correct effort levels (High)

- `split/agents/senior-dev/senior-dev.md`: Change `effort: medium` to `effort: high`
- `split/agents/technical-writer/technical-writer.md`: Change `effort: low` to `effort: medium`

#### 2c. Clarify WebSearch/WebFetch status in Researcher (Low — original finding was wrong)

Research confirmed `WebSearch` and `WebFetch` are **built-in Claude Code tools**, not MCP-dependent. The official Anthropic `feature-dev` plugin uses them. Keep them in the Researcher's tool list.

**Known issue:** GitHub [#21318](https://github.com/anthropics/claude-code/issues/21318) documents that marketplace plugin agents may fail to use `WebSearch`/`WebFetch` despite listing them. Test on current version; if broken, add a graceful degradation note: "If WebSearch/WebFetch are unavailable, note the limitation and fall back to Bash with curl for raw HTTP fetches."

**No change needed unless the bug is confirmed active.**

#### 2d. Gate or remove Agent tool from Tech Lead (High)

`split/agents/tech-lead/tech-lead.md` lists `Agent` with no usage guidance.

**Fix:** Remove `Agent` from the Tech Lead's tool list. The Tech Lead does not need to spawn sub-agents -- the orchestrator handles all dispatch. If sub-delegation is needed in the future, it should be re-added with explicit rules.

#### 2e. Add outcome protocol to all personas (Medium)

The outcome reporting protocol (`completed`, `failed`, `needs_input`, `already_satisfied`) exists only in the orchestrator preamble. If the preamble is truncated, personas don't know how to report outcomes.

**Fix:** Add the following to each persona's `.md` file (after the "How You Work" section):

```
## Reporting Outcomes

End your response with exactly one of:
- `Outcome: completed` -- work is done
- `Outcome: already_satisfied` -- acceptance criteria were already met (include evidence)
- `Outcome: failed -- <reason>` -- could not complete
- `Outcome: needs_input -- <question>` -- need a decision from the user
```

#### 2f. Add Write tool to Security Reviewer (Medium)

`split/agents/security-reviewer/security-reviewer.md` has read-only tools but is expected to produce threat model documents.

**Fix:** Add `Write` to the tools list: `tools: Read, Grep, Glob, Bash, Write`

#### 2g. Add Edit tool to SME (Medium)

`split/agents/sme/sme.md` has `Write` but not `Edit`, making targeted spec revisions risky (full-file overwrite).

**Fix:** Add `Edit` to the tools list: `tools: Read, Grep, Glob, Bash, Edit, Write`

#### 2h. Fix "ask another persona" instruction (Medium)

`split/agents/shared/core-operating-principle.md` line 12 says "Ask another persona internally first" -- agents cannot do this.

**Fix:** Replace with: "If your question is about another persona's domain, report `Outcome: needs_input` with a description of what you need. The orchestrator will route it to the appropriate persona."

Since we are inlining this file (2a), this fix applies to the inlined content in all 11 agents and to the canonical source file.

#### 2i. Add `isolation: "worktree"` to file-writing agents (Medium — new finding)

Plugin agents support `isolation: "worktree"` in frontmatter. This runs the agent in a temporary git worktree, keeping its file changes out of the user's working tree. Changes are either merged or discarded when the agent finishes.

**Important caveat:** This is git isolation only. The agent still runs in the same session and permission prompts still fire for every tool use. It does not bypass permissions.

**Fix:** Add `isolation: worktree` to agents that write files:
- `senior-dev`, `test-writer`, `technical-writer`, `ux-designer`, `devops`, `security-reviewer`

Read-only agents (code-reviewer, verifier, researcher, tech-lead, sme) do not need it.

#### 2j. Document the permission prompt situation (Low — new finding)

**Context from research:**
- `permissionMode` is blocked for all plugin agents (by design, for security). All values (`acceptEdits`, `auto`, `bypassPermissions`) are unsupported.
- Plugin `settings.json` only supports `agent` and `subagentStatusLine` — cannot set `permissions.allow`.
- There is a known bug ([#18950](https://github.com/anthropics/claude-code/issues/18950)) where sub-agents don't reliably inherit "Allow for session" permission approvals from the parent session.
- `PreToolUse` hooks *do* reliably propagate to sub-agents (unlike permission rules).

**Consequence:** Users will see permission prompts for `Write`, `Edit`, `WebSearch`, `WebFetch`, and `Bash` operations from agents. This is unavoidable without invasive session-wide permission injection. Document this in the README as a known limitation.

**Fix:** Add a note to the README: "Agents will prompt for tool permissions during execution. Approve once per session for each tool type. This is a Claude Code limitation for marketplace plugins."

---

### M003: Orchestrator (SKILL.md) fixes

**Goal:** Fix missing workflow steps and ambiguities in the orchestrator protocol.

All changes are to `split/skills/split/SKILL.md` unless otherwise noted.

#### 3a. Add `--tokens-used` to ticket update examples (High)

The `ticket update --status done` examples omit `--tokens-used`. Note: the CLI currently has no `--tokens-used` flag.

**Two-part fix:**
1. Add `--tokens-used` as an optional argument to the `ticket update` CLI command in `cli.py` and handle it in `cmd_ticket_update` in `commands.py` (store in the ticket dict as `tokens_used`).
2. Update the SKILL.md examples to include `--tokens-used <N>`.

#### 3b. Restore structured outcome handling (High)

The review notes that simplified versions of SKILL.md removed `already_satisfied`, `failed`, and `needs_input` outcome handling.

**Status:** The current SKILL.md (lines 140-166) already has all four outcome branches (`completed`, `already_satisfied`, `failed`, `needs_input`). Verify during implementation that these are complete and correct. If they are, mark this as already addressed.

#### 3c. Add `in_progress` step before agent dispatch (Medium)

No instruction exists to set tickets to `in_progress` before dispatching. Interrupted sessions leave dispatched tickets as `backlog`.

**Fix:** Add to Phase 3, step 3, before agent dispatch:
```
split-board ticket update --id TXXX --status in_progress
```

#### 3d. Clarify complexity classification (Medium)

The boundary between "Medium" and "Complex" is vague, and "Medium" says "no milestones" but `ticket add` requires `--milestone`.

**Fix:** Rewrite the complexity classification:
- **Medium** -- 2-5 tickets, single milestone. Create one milestone and assign all tickets to it.
- **Complex** -- 6+ tickets or cross-cutting concerns. Group into multiple milestones with dependency ordering.

#### 3e. Add "n" handler for session resumption (Medium)

The `Continue? [y/n]` prompt has no defined behavior for "n".

**Fix:** Add: "If the user answers **n**: summarize remaining work (tickets left, milestones incomplete), save board state, and exit. Do not dispatch any agents."

#### 3f. Add merge conflict guidance in Phase 5 (Low -- included because trivial)

**Fix:** Add to Phase 5: "If merge conflicts arise when merging the worktree branch, resolve them in the worktree, run the Verifier on affected files, then retry the merge."

---

### M004: Hook and plugin structure fixes

**Goal:** Make hooks reliable and fix plugin structure issues that may cause agent loading problems.

#### 4a. Replace `settings.local.json` injection with `PermissionRequest` hook (High)

**Background (from research):** The current approach of directly writing to `.claude/settings.local.json` from a `SessionStart` hook is invasive and fragile — it requires `jq`, has a race condition with concurrent sessions, and modifies the user's project files without visible consent.

The better approach is a `PermissionRequest` hook that intercepts the permission dialog for `split-board` commands and auto-approves them. This is the documented API for this pattern, shows the `[Plugin: split]` label in the dialog, and does not touch any settings files.

**Changes to `split/hooks/hooks.json`:**

Add a `PermissionRequest` hook entry:
```json
"PermissionRequest": [{
  "matcher": "Bash",
  "hooks": [{
    "type": "command",
    "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/approve-split-board.sh\"",
    "timeout": 5
  }]
}]
```

**New file `split/hooks/approve-split-board.sh`:**

```sh
#!/bin/sh
# Auto-approve Bash(split-board:*) permission requests for the split plugin.
INPUT="$(cat)"
cmd=$(echo "$INPUT" | jq -r '.tool_input.command // empty' 2>/dev/null)
case "$cmd" in
  split-board*)
    echo "split plugin: auto-approving split-board command"
    printf '{"decision":"allow","reason":"split-board is the split plugin CLI"}'
    exit 0
    ;;
esac
exit 0  # pass through all other permission requests unchanged
```

**Remove `install-cli.sh` or reduce it to install-only logic** (no settings modification). If removal is premature, keep it but make it transparent (see 4c).

**Note on `jq` dependency:** If using the `PermissionRequest` approach, `jq` is only needed for extracting the command from the hook input. If `jq` is absent, the hook falls back to `exit 0` (pass through), meaning `split-board` will still prompt — but won't silently corrupt settings.

#### 4b. Fix `install-cli.sh` temp file race condition (High — only if keeping `install-cli.sh`)

Two concurrent sessions writing to the same `.tmp` file causes data loss.

**Fix:**
```sh
tmp=$(mktemp "${SETTINGS_FILE}.XXXXXX")
trap 'rm -f "$tmp"' EXIT
jq ... "$SETTINGS_FILE" > "$tmp" && mv "$tmp" "$SETTINGS_FILE"
```

#### 4c. Print consent message before modifying settings (High — only if keeping `install-cli.sh`)

**Fix:** Add before any write operation:
```sh
echo "split plugin: adding Bash(split-board:*) to .claude/settings.local.json for auto-approval" >&2
```

#### 4d. Fix grep specificity in install-cli.sh (Medium — only if keeping `install-cli.sh`)

`grep -q 'split-board'` is too broad -- matches comments.

**Fix:** Change to: `grep -q '"Bash(split-board:\*)"' "$SETTINGS_FILE"`

#### 4e. Improve guard-board.sh JSON matching (Medium)

Shell `case` pattern matching on raw JSON is fragile.

**Fix:** If `jq` is available, use it:
```sh
if command -v jq >/dev/null 2>&1; then
  file_path=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
else
  file_path="$INPUT"  # fall back to current behavior
fi
```
Then match against `$file_path` instead of `$INPUT`.

#### 4f. Add timeout to hooks (Low -- included because trivial and prevents hangs)

**Changes to `split/hooks/hooks.json`:**

Add `"timeout": 10` to both hook entries. Remove `"async": false` (non-standard field).

#### 4g. Flatten agent subdirectory structure (Medium)

**Depends on M002a completing first** (content inlining must happen before files are moved).

Agents use `agents/<name>/<name>.md` instead of the standard `agents/<name>.md`.

**Fix:** Move each agent file from `split/agents/<name>/<name>.md` to `split/agents/<name>.md` and remove the now-empty subdirectories. Update any references in SKILL.md if they exist.

#### 4h. Relocate `agents/shared/` to avoid agent loader confusion (Medium)

`split/agents/shared/core-operating-principle.md` has no agent frontmatter but sits in `agents/`, potentially confusing Claude Code's agent loader.

**Fix:** Move to `split/prompts/core-operating-principle.md`. Since we're inlining the content (M002, 2a), this file becomes reference-only. Update any remaining references.

#### 4i. Deduplicate version and fix marketplace.json schema (Medium)

- Remove `"version": "0.1.0"` from `.claude-plugin/marketplace.json` (let `plugin.json` be the source of truth).
- Remove `"version"` and `"author"` from the plugin entry inside `marketplace.json` for the same reason.
- Move `metadata.description` to top-level `description` in `marketplace.json`.
- Add `"$schema": "https://anthropic.com/claude-code/marketplace.schema.json"` to `marketplace.json`.

---

### M005: CLI correctness

**Goal:** Fix data integrity issues in the board CLI.

#### 5a. Guard `load_board` against empty YAML (Medium)

`yaml.safe_load` returns `None` for an empty file, causing downstream `AttributeError`.

**Changes to `split/tools/src/split_board/board.py`:**

```python
def load_board(board_path: Path) -> dict:
    with open(board_path) as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        error(f"Board file is empty or corrupt: {board_path}")
    return data
```

#### 5b. Add atomic writes to `save_board` (Medium)

Parallel agents can corrupt `board.yaml` with concurrent writes.

**Fix:** Use atomic write (write to temp file, then `os.replace`). Do NOT use `fcntl.flock` on a truncating `open(..., "w")` — that pattern truncates the file before the lock is acquired, so a second process can truncate and then overwrite the first writer's data.

```python
import os, tempfile

def save_board(board: dict, board_path: Path) -> None:
    dir_ = board_path.parent
    with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp") as f:
        yaml.dump(board, f, default_flow_style=False, sort_keys=False)
        tmp_path = f.name
    os.replace(tmp_path, board_path)
```

`os.replace` is atomic on POSIX systems (rename syscall). Apply the same pattern to the `metrics.yaml` write.

#### 5c. Add duplicate ID/milestone validation (Medium)

`validate_board` silently deduplicates IDs via set comprehension.

**Changes to `split/tools/src/split_board/validation.py`:**

Before building the `ticket_ids` set, check for duplicates:
```python
all_ids = [t["id"] for t in all_tickets]
seen = set()
for tid in all_ids:
    if tid in seen:
        errors.append(f"Duplicate ticket ID: {tid}")
    seen.add(tid)
```

Same for milestone IDs.

#### 5d. Add `recompute_ticket_blocked_statuses` comment (High)

**Changes to `split/tools/src/split_board/validation.py`:**

Add a docstring or inline comment to `recompute_ticket_blocked_statuses` explaining: "Intentional: backlog tickets with unresolved dependencies are forced to `blocked` to prevent premature dispatch by the orchestrator."

---

### M006: Test coverage

**Goal:** Add tests for untested critical paths identified in the review.

#### 6a. Add `cmd_dashboard` path resolution test (High)

Mock `importlib.resources.files` and verify `cmd_dashboard` resolves the correct `_dashboard.py` path. Also mock `subprocess.run` to avoid actually launching the TUI.

#### 6b. Add dashboard module smoke test (High)

Test that `_dashboard.py` can be imported and that key classes/functions exist. Test pure data formatting functions (e.g., `COLUMN_INDEX` mapping, ticket style resolution) without launching the TUI.

#### 6c. Update error path tests for `BoardError` (follows from M001)

After the `error()` refactor, update all existing error tests to use `pytest.raises(BoardError)`. Add `capsys` assertions to verify error messages. Verify exception messages contain actionable guidance.

#### 6d. Add cycle detection test (Medium)

Add a test with tickets A -> B -> A and verify `has_cycle` returns `True`. Add a test with A -> B -> C (no cycle) returning `False`.

#### 6e. Add `spec list --status` filtering test (Medium)

Create specs, archive one, filter by `--status active`, verify only active specs appear.

#### 6f. Add `resolve_spec_dir` archive fallback test (Medium)

Place a spec in `archive/`, call `resolve_spec_dir` with its ID, verify it is found.

#### 6g. Add `ticket update` no-op test (Medium)

Call `ticket update --id TXXX` with no other flags. Verify the command completes without error and the board is unchanged.

#### 6h. Add error message assertion tests (Medium)

For key error paths (invalid transition, missing dependency, missing artifact), verify the error message contains the expected guidance text using exception string matching.

---

### M007: Documentation

**Goal:** Fix incorrect or misleading documentation.

#### 7a. Fix README "Local development" section (High)

The "Local development" section is an exact copy of "Install". Replace with:
```
claude plugin install --source /path/to/claude-split/split
```
Show how to install from a local checkout for contributors.

#### 7b. Verify and fix install syntax (High)

The `split@claude-split` syntax in the README is unverified. Verify the correct marketplace install syntax against the Claude Code CLI docs. If the current syntax is wrong, fix it. If it cannot be verified, add a note: "Install syntax may vary by Claude Code version."

#### 7c. Fix uv prerequisite claim (Medium -- included because factually incorrect)

README line 81 says "uv ... installed automatically on session start." `install-cli.sh` does not install `uv`.

**Fix:** Change to: "Requires [uv](https://docs.astral.sh/uv/) to be installed."

#### 7d. Add concrete usage example (Medium)

Add a "Quick start" section to the README showing a 3-5 line sample interaction:
```
You: /split
Claude: What would you like to build? ...
You: Add rate limiting to the API
Claude: [SME] Let me ask a few questions...
```

#### 7e. Verify and update dashboard PATH caveat (Medium)

The README says `split-board` is not on PATH. The `bin/split-board` wrapper should be on PATH via Claude Code's plugin `bin/` mechanism. If so, remove the caveat. If not, update with accurate workaround.

---

## Acceptance Criteria

### M001 (Critical)
- [ ] `error()` raises `BoardError` instead of calling `sys.exit(1)`
- [ ] `error()` has return type annotation `-> Never`
- [ ] `cli.py:main()` catches `BoardError` and calls `sys.exit(1)` with the error message
- [ ] All existing tests pass with `BoardError` instead of `SystemExit`
- [ ] SKILL.md uses `git worktree add` commands, not `EnterWorktree` pseudo-code
- [ ] SKILL.md defines `WORKTREE_ROOT` and all agent path references use it
- [ ] SKILL.md passes `--base-dir` pointing to the worktree's `.claude/split`

### M002 (Personas)
- [ ] Core operating principle content is inlined in all 11 agent files
- [ ] No agent file contains `@agents/shared/` import lines
- [ ] Senior Dev effort is `high`; Technical Writer effort is `medium`
- [ ] Researcher does not list `WebSearch` or `WebFetch`
- [ ] Tech Lead does not list `Agent`
- [ ] All 11 personas include the outcome protocol section
- [ ] Security Reviewer has `Write` in tools
- [ ] SME has `Edit` in tools
- [ ] "Ask another persona" instruction is replaced with `needs_input` routing

### M003 (Orchestrator)
- [ ] CLI supports `--tokens-used` on `ticket update`
- [ ] SKILL.md examples include `--tokens-used`
- [ ] SKILL.md includes `ticket update --status in_progress` before agent dispatch
- [ ] Complexity classification defines concrete criteria and clarifies single-milestone for medium tasks
- [ ] Session resumption "n" handler is defined
- [ ] Phase 5 includes merge conflict guidance

### M004 (Hooks & structure)
- [ ] `install-cli.sh` prints a warning when `jq` is missing
- [ ] `install-cli.sh` uses `mktemp` for temp files
- [ ] `install-cli.sh` prints a consent message before modifying settings
- [ ] `install-cli.sh` grep pattern matches `"Bash(split-board:*)"` exactly
- [ ] `guard-board.sh` uses `jq` for field extraction when available
- [ ] `hooks.json` has `"timeout": 10` on both hooks and no `"async"` field
- [ ] Agent files are at `split/agents/<name>.md` (flat, no subdirectories)
- [ ] `shared/core-operating-principle.md` is moved to `split/prompts/`
- [ ] `marketplace.json` has no duplicate version, has `$schema`, has top-level `description`

### M005 (CLI correctness)
- [ ] `load_board` raises `BoardError` on empty/corrupt YAML
- [ ] `save_board` uses file locking or atomic writes
- [ ] `validate_board` detects duplicate ticket and milestone IDs
- [ ] `recompute_ticket_blocked_statuses` has explanatory documentation

### M006 (Tests)
- [ ] `cmd_dashboard` has a test that mocks `importlib.resources.files` and `subprocess.run`
- [ ] Dashboard module has a smoke test (import + data function tests)
- [ ] Cycle detection has tests for both cyclic and acyclic graphs
- [ ] `spec list --status` filtering is tested
- [ ] `resolve_spec_dir` archive fallback is tested
- [ ] `ticket update` no-op case is tested
- [ ] Error path tests verify messages, not just exception type
- [ ] All tests pass

### M007 (Documentation)
- [ ] README "Local development" shows local path install
- [ ] README install syntax is verified or annotated
- [ ] README says uv is a prerequisite (not auto-installed)
- [ ] README has a Quick start example
- [ ] README dashboard PATH caveat is accurate
