# Split Board CLI — Design Spec

A Python CLI tool that serves as the sole interface for creating and mutating Split board state. Personas never write board YAML directly — they call this tool, which enforces every structural, value, and semantic constraint by construction.

## Problem

The Split orchestrator and personas produce YAML files (boards, tickets) that must conform to strict schemas and cross-field invariants. LLMs generating raw YAML will drift — missing fields, invalid statuses, circular dependencies, broken references. Post-hoc validation catches errors after the damage is done. The better approach: make invalid state unrepresentable by routing all mutations through a tool that enforces the rules.

## Design Principles

1. **Correctness by construction** — the tool produces valid YAML or returns an error. There is no "write first, validate later" path.
2. **LLM-friendly errors** — every error message names the exact constraint violated and suggests the command to fix it.
3. **Self-documenting** — `--help` on any subcommand explains what it does, what's required, and what rules apply. Personas can also read the source to understand why something is failing.
4. **Human-readable output** — YAML for all persisted state. Personas and humans can read board files directly for context.
5. **Zero external dependencies** — Python stdlib plus PyYAML only.

## ID Format

All IDs use a short prefix and zero-padded sequential number:

- **Specs:** `S001`, `S002`, ...
- **Milestones:** `M001`, `M002`, ...
- **Tickets:** `T001`, `T002`, ... Follow-ups append a letter: `T003a`, `T003b`

IDs are scoped to their context — ticket IDs are unique within a board, milestone IDs within a board, spec IDs globally across all specs. The tool auto-generates the next available ID in each scope.

## Spec Directory Structure

Each spec gets its own directory under `.claude/split/`. The directory name combines the spec ID with a slug derived from the title for human readability:

```
.claude/split/
├── active/
│   ├── S001-rate-limiting/
│   │   ├── spec.md               # The approved spec document
│   │   ├── board.yaml            # Tickets, milestones, decisions, metrics
│   │   ├── log.md                # Append-only execution log
│   │   └── artifacts/            # Approach docs, review notes, etc.
│   └── S002-auth-refactor/
│       └── ...
└── archive/
    └── S000-initial-setup/
        └── ...
```

The slug is generated at init time: lowercase the title, replace non-alphanumeric characters with hyphens, collapse consecutive hyphens, truncate to 40 characters.

Multiple specs can be active simultaneously. When commands need to target a spec, `--spec` accepts either the full directory name (`S001-rate-limiting`) or just the ID (`S001`). When only one spec is active, `--spec` is optional and defaults to that spec.

## CLI Interface

### Spec Lifecycle

```
split-board spec list
split-board spec list --status active
split-board spec list --status archived
```

- Scans `active/` and `archive/` directories
- Prints spec IDs, titles (from each `board.yaml`), and statuses

```
split-board spec init --title "Rate limiting" --complexity complex
split-board spec init --title "Quick bugfix" --complexity medium
```

- `--complexity` accepts `complex` or `medium`
- Auto-generates the next spec ID by scanning existing directories
- Slugifies the title and creates `.claude/split/active/S001-<slug>/`
- Initializes `board.yaml` with metadata, empty `log.md`, and `artifacts/` directory
- Prints the created spec ID and path

```
split-board spec archive --spec S001
split-board spec abandon --spec S001
```

- `--spec` is required for these commands (no default — destructive operations must be explicit)
- Moves the spec directory from `active/` to `archive/`
- Updates the board's `status` field to `archived` or `abandoned`

### Ticket Operations

```
split-board ticket add --title "Design approach" \
  --persona tech-lead \
  --acceptance-criteria "Approach doc covering algorithm, limits, storage" \
  --produces approach-doc \
  --milestone M001 \
  --depends-on T001,T002 \
  --requires-approval \
  --spec S001
```

- Auto-generates the next ticket ID within the board
- Validates persona against available persona definitions
- If `--milestone` is provided, places the ticket in that milestone
- If `--depends-on` is provided, validates that referenced tickets exist and that adding the dependency doesn't create a cycle
- Sets initial status to `backlog` if no dependencies, `blocked` if dependencies exist
- All flags except `--title`, `--persona`, `--acceptance-criteria`, and `--produces` are optional

```
split-board ticket update --id T001 --status done --tokens-used 18200 --artifact artifacts/T001-approach.md
split-board ticket update --id T002 --status in_progress
split-board ticket update --id T003 --status failed
```

Enforced invariants on status transitions:
- `in_progress` — all dependencies must be `done`
- `done` — requires `--tokens-used` (> 0) and at least one `--artifact` (either provided in this command or already present on the ticket)
- `pending_approval` — same requirements as `done`, plus `requires_approval` must be `true` on the ticket
- `failed` — records the current state; downstream tickets are not auto-updated (the orchestrator handles retry/reassign/skip)
- `skipped` — downstream tickets depending solely on this ticket are marked `blocked_by_skip`

```
split-board ticket add-dependency --id T002 --depends-on T001
split-board ticket remove-dependency --id T002 --depends-on T001
```

- Validates referenced tickets exist
- Checks for dependency cycles before writing
- Updates ticket status (`blocked`/`backlog`) as appropriate

### Follow-up Tickets

```
split-board followup create --parent T003 \
  --persona senior-dev \
  --title "Fix race condition" \
  --acceptance-criteria "Mutex on counter increment, verified under concurrent load" \
  --produces implementation
```

- Auto-generates ID as `T003a`, `T003b`, etc. based on the parent ticket number
- Sets `created_by` to the parent ticket ID
- Adds the new ticket ID to the parent's `follow_ups` array
- Adds dependency on the parent ticket
- Places the follow-up in the same milestone as the parent
- Enforces the two-level follow-up limit from the spec: a follow-up of a follow-up cannot itself generate further follow-ups

### Milestone Operations

```
split-board milestone add --title "Design & core"
split-board milestone add --title "Integration & hardening"
```

- Auto-generates the next milestone ID (M001, M002, ...)
- Only valid when `complexity` is `complex`
- New milestones are created with status `blocked`

```
split-board milestone move-ticket --ticket T001 --milestone M001
```

- Moves a ticket from its current location to the specified milestone
- Validates the milestone exists

Milestone status is managed automatically:
- The first milestone with incomplete tickets is `active`
- All subsequent milestones are `blocked`
- When all tickets in a milestone reach `done`, the next milestone becomes `active`

### Decision Recording

```
split-board decision add --ticket T002 \
  --question "Redis or in-memory for rate limit storage?" \
  --answered-by user \
  --answer "Redis — we need this to work across multiple instances"
```

- Appends to the board's `decisions` array
- Auto-timestamps

### Metrics

Metrics are computed, not manually set. The tool recalculates the `metrics` block on every write operation:

- `started` — set once on `spec init`
- `agent_dispatches` — count of tickets that have ever been `in_progress`
- `total_tickets` — count of all tickets
- `completed_tickets` — count of tickets with status `done`
- `follow_up_tickets` — count of tickets with a `created_by` field
- `user_questions` — count of decisions where `answered_by` is `user`
- `milestones_completed` — count of milestones where all tickets are `done`
- `total_tokens` — sum of all `tokens_used` across tickets

### Board Inspection

```
split-board status
split-board status --spec S001
```

- Pretty-prints the board in the same format as the `/status` skill output
- When `--spec` is omitted and multiple specs are active, shows all of them
- When `--spec` is omitted and one spec is active, shows that one

```
split-board validate
split-board validate --spec S001
```

- Runs the full validation suite against the board (useful for checking boards that were created before this tool existed or after manual recovery from git)
- Reports all violations, not just the first

### Persona Validation

```
split-board persona validate agents/tech-lead/tech-lead.md
split-board persona validate-all agents/
split-board persona list agents/
```

The agents directory path is relative to the plugin installation. The tool resolves it from its own location (i.e., `../agents/` relative to `tools/split_board.py`).

**Frontmatter schema enforced:**
- `name` (required): string, pattern `^[a-z][a-z0-9-]*$`
- `description` (required): string
- `memory` (required): enum `project`, `user`
- `model` (required): enum `opus`, `sonnet`, `haiku`
- `effort` (required): enum `low`, `medium`, `high`, `max`
- `tools` (required): array of strings from known Claude Code tool names
- No additional properties allowed

`persona list` outputs available persona names — this is what the board commands use internally to validate `--persona` values.

### Spec Disambiguation

When multiple specs are active, most commands require `--spec`. If omitted:
- **One active spec** — defaults to that spec silently
- **Multiple active specs** — returns an error listing the active specs:
  ```
  ERROR: Multiple active specs. Specify one with --spec:
    S001-rate-limiting: "Rate limiting" (active since 2026-04-10)
    S002-auth-refactor: "Auth refactor" (active since 2026-04-11)
  ```
- **No active specs** — returns an error suggesting `split-board spec init`

## Hook Guard

A Claude Code `PreToolUse` hook prevents personas from bypassing the CLI:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "command": "python tools/split_board.py guard \"$TOOL_INPUT\""
      }
    ]
  }
}
```

The `guard` subcommand inspects the target file path in the tool input. If it matches `board.yaml` within the `.claude/split/` directory, it exits non-zero with:

```
Board files must be modified through split-board commands, not written directly.
Run: split-board --help
```

This applies to all personas and the orchestrator. The only way to mutate board state is through the CLI.

## Validation Rules

All rules are enforced at mutation time. The `validate` command runs them all for ad-hoc checking.

### Structural Rules (per-field)
- All required fields present on tickets, milestones, board metadata
- Field types correct (strings, integers, arrays, enums)
- ID formats: specs `S\d{3}`, milestones `M\d{3}`, tickets `T\d{3}[a-z]?`
- Enum values: status fields, persona frontmatter enums
- No additional/unknown properties

### Referential Rules (cross-field)
- Every `depends_on` entry references an existing ticket ID in the same board
- Every `persona` value matches an available persona definition
- Every `created_by` value references an existing ticket that lists this ticket in `follow_ups` (and vice versa)
- Every ticket in a milestone references a milestone that exists

### Semantic Rules (invariants)
- No circular dependencies
- Completed tickets (`done`) have `tokens_used > 0` and at least one artifact
- Tickets with unresolved dependencies cannot be `in_progress` or `done`
- Only the first non-completed milestone can be `active`; subsequent ones are `blocked`
- Follow-ups are limited to two levels deep (a follow-up's follow-up cannot spawn further follow-ups)
- Computed metrics match actual board state

## Error Output Format

**Success:**
```
OK: Ticket T001 added to S001-rate-limiting (milestone M001)
```

**Failure:**
```
ERROR: Cannot set T002 to in_progress
  Reason: Dependency T001 has status 'backlog' (must be 'done')
  Fix: Complete T001 first:
    split-board ticket update --id T001 --status done --tokens-used <N> --artifact <path>
  Or remove the dependency:
    split-board ticket remove-dependency --id T002 --depends-on T001
```

Every error includes: what failed, why, and the command(s) to resolve it.

## File Structure Within the Plugin

```
split/
├── tools/
│   └── split_board.py        # The CLI tool (single file)
├── agents/                    # Persona definitions (validated, not generated)
│   └── ...
├── skills/                    # Orchestrator, retro, status skills
│   └── ...
├── dashboard.html             # Static board viewer (reads the same YAML)
└── settings.json              # Plugin settings including hook guard
```

The tool lives at `tools/split_board.py` within the plugin. It is invoked by personas and the orchestrator via `python tools/split_board.py <command>`.

## Runtime Characteristics

The tool is stateless — all state lives in the YAML files under `.claude/split/`. The tool reads, validates, mutates, and writes. Git provides versioning and recovery (the orchestrator commits after every state change, as specified in the Split design).

## Interaction with the Dashboard

The dashboard (`dashboard.html`) is a read-only YAML viewer. Because the CLI tool produces conformant YAML, the dashboard can parse it reliably. The schema is the contract between the CLI tool (writer) and the dashboard (reader).

## Scope Boundaries

This tool covers board state management only. It does not:
- Dispatch persona-agents (that's the orchestrator skill)
- Append to `log.md` (that's the orchestrator skill, append-only text)
- Write spec documents (that's the SME persona)
- Manage the retro process (that's the `/retro` skill)
- Generate or modify persona markdown (that's human-authored or retro-proposed)
