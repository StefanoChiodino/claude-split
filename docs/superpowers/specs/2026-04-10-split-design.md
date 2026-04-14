# Split — Design Spec

A Claude Code plugin that turns a single AI session into a team of specialized personas, coordinated by an LLM-powered orchestrator through a kanban board system.

Think of it as a company of specialists — each member has their own role, objectives, and accountability, all working together on the same project.

## How It Maps to Claude Code

Split is a **plugin** — the installable package. Inside it are **agents** (the persona definitions — Tech Lead, Test Writer, Senior Dev, etc.) and **skills** (the user-facing commands — `/split`). The orchestrator is a skill that dispatches agents. The user interacts with skills; agents do the work.

## Core Concepts

Split has four pillars:

1. **Personas** — Markdown-defined Claude Code agents, each with a role, objectives, what they optimize for, and persistent memory. Ships with a default team; users extend by adding markdown files.

2. **Orchestrator** — A skill (`/split`) that drives a spec-first workflow: the user talks to a Subject Matter Expert, the spec is reviewed internally by the Tech Lead, then the orchestrator creates tickets on the kanban board. The user invokes `/split` explicitly, or Claude auto-invokes it when the task warrants the full team.

3. **Kanban Board** — A file-based board tracking all work. Each spec gets its own board. Tickets have assigned personas, dependencies, acceptance criteria, and artifact references. An execution engine walks the board, dispatching unblocked tickets to persona-agents.

4. **Retro Engine** — At session end, the team reviews what happened: what worked, what didn't, and proposes updates to persona definitions, workflow patterns, and project-level configuration. The human reviews all changes.

## Personas

Each persona is a Claude Code custom agent defined as a markdown file. Agents live in two locations:

- **Plugin agents** — shipped with Split, at `<plugin-root>/agents/<persona-name>/<persona-name>.md`. These are the default team (Tech Lead, Senior Dev, Test Writer, etc.).
- **Project agents** — user-defined, at `<project-root>/.claude/agents/<persona-name>/<persona-name>.md`. Users drop markdown files here to add personas specific to their project.

Project-level agents take priority over plugin agents with the same name. The orchestrator discovers agents from both locations automatically.

This gives each persona its own full system prompt (strongest behavioral shaping) and persistent memory.

### Persona Definition Structure

```yaml
---
name: tech-lead
description: Architectural decisions, approach design, trade-off analysis
model: opus
effort: high
tools: Read, Grep, Glob, Bash, Edit, Write, Agent
---

You are the Tech Lead on this team.

## Your Objectives
- Design coherent, maintainable architectures
- Catch over-engineering and unnecessary complexity early
- Ensure changes fit the broader system context

## What You Optimize For
- Simplicity and coherence over cleverness
- Consistency with existing patterns
- Clear boundaries between components

## How You Work
- When given a task, you produce an approach document
- You consider 2-3 alternatives before recommending one
- You flag risks and open questions explicitly

## Core Operating Principle
Your job depends on getting this right, not on being fast. When you encounter
anything ambiguous, underspecified, or where multiple valid options exist — stop
and ask the user. Present options with your recommendation, but never proceed on
an assumption. A question that feels obvious to you might reveal a constraint
you don't know about.
```

Every persona includes the "Core Operating Principle" section above — the mandate to ask rather than assume. Rather than duplicating it in every persona file, each persona references a shared file using `@agents/shared/core-operating-principle.md`. This keeps the principle in one place and avoids drift across persona definitions.

### Frontmatter Fields

- **`name`** (string) — Identifier used in ticket assignment and agent dispatch.
- **`description`** (string) — One-line summary of the persona's role. Used by the orchestrator to decide which personas are relevant.
- **`model`** (enum: `opus` | `sonnet` | `haiku`) — Which Claude model the persona uses.
- **`effort`** (enum: `low` | `medium` | `high` | `max`) — Claude Code's reasoning effort parameter. Controls how much thinking the model does before responding. `low` for straightforward tasks (documentation), `medium` for standard implementation, `high` for complex reasoning (architecture, adversarial review), `max` for deep investigation (research).
- **`tools`** (string[]) — Which Claude Code tools the persona has access to.

### Default Team

| Persona | Role | Effort | When Activated |
|---------|------|--------|----------------|
| **SME** | Domain expert, user-facing dialogue, spec drafting | high | Every split (spec phase) |
| **Tech Lead** | Feasibility, architecture, system constraints, spec compliance review | high | Every spec (internal review) + compliance review |
| **Test Writer** | Writes tests from acceptance criteria before implementation | high | Code tickets (before implementation) |
| **Senior Dev** | Implementation, test review, debugging | medium | Code changes, debugging |
| **Code Reviewer** | Code quality, patterns, maintainability | high | After implementation |
| **Verifier** | Final verification — acceptance criteria met, artifacts correct | high | Every ticket (adapts approach to ticket type) |
| **Researcher** | Deep investigation — legal, compliance, market, technical feasibility | max | Knowledge gathering before decisions |
| **UX Designer** | UI/UX patterns, accessibility, user flows, interaction design | medium | Any user-facing interface work |
| **DevOps** | Infrastructure, CI/CD, deployment, monitoring, performance | medium | Infra changes, deployment, performance |
| **Security Reviewer** | Threat modeling, vulnerability analysis, auth/authz | high | Security-sensitive changes, auth, data handling |
| **Technical Writer** | Documentation, API docs, user guides, changelog | low | When deliverables include documentation |

### Extension

Users add personas by dropping a markdown file in their project's `.claude/agents/` directory. The orchestrator automatically discovers available personas from the agents directory. A fintech team might add a Compliance Officer; a gamedev team might add a Game Designer.

Users can override a default persona by creating one with the same name in their project — project-level agents take priority over plugin agents.

### Memory

Personas are stateless between sessions. There is no separate memory layer — a persona's entire knowledge comes from its system prompt definition, the spec, the board, and the artifacts produced by other tickets.

The retro process is the sole mechanism for persona evolution. When the retro identifies patterns ("the Tech Lead keeps missing backwards compatibility concerns"), it proposes changes directly to the persona's markdown definition file. Over time, persona definitions become specialized — not through accumulated memory files, but through iterative refinement of their system prompts.

## The Orchestrator

The orchestrator is the brain of Split. It is implemented as a single skill (`/split`) that drives the entire spec-first workflow.

### Mechanism — Skill-Based Orchestration

The `/split` skill is the sole entry point. There is no hook intercepting every prompt — the orchestration only activates when:

1. **The user explicitly invokes `/split`** — "I want to implement X Y"
2. **Claude auto-invokes the skill** — based on the skill's `description` field, Claude recognizes when a task warrants the full Split workflow (e.g., multi-component features, complex cross-cutting changes)

When activated, the skill scans the `active/` directory for existing specs. If an active spec exists, it resumes that spec's workflow. If not, it starts a new spec-first workflow.

**Resuming work:** The user just invokes `/split` again in a new session. Since the skill scans `active/` on every invocation, it picks up where things left off — no special syntax needed. If multiple specs are active, the skill lists them and asks which one to resume. The user can also be specific in plain English: `/split` followed by "resume the rate limiting work" or "continue S002".

This means simple tasks (typo fixes, quick questions, small changes) never touch the orchestration — they're handled by normal Claude Code interaction. Split only engages when there's real work that benefits from the team structure.

### Execution Engine

The orchestration skill acts as the execution engine. After tickets are created, it:

1. Reads the board file to find the current active milestone and its unblocked tickets (all dependencies in `done` status)
2. Dispatches each unblocked ticket to its assigned persona via the Agent tool. Tickets within a milestone that have no dependencies between them can be dispatched in parallel.
3. The persona-agent receives the ticket context (acceptance criteria, spec reference, artifacts from dependency tickets) as its prompt
4. When the agent completes, the skill records token usage on the ticket, updates the board (status, artifacts, metrics), commits the board state to git, and appends to the execution log
5. If the ticket has `requires_approval: true`, it moves to `pending_approval` — the skill surfaces the output to the user and blocks downstream tickets until the user approves (see Approval Gates)
6. If the persona-agent has questions for the user, it returns them — the skill surfaces these directly to the user, tagged with the persona's identity and ticket ID, and feeds the answers back
7. When the Code Reviewer or Verifier produces blockers, follow-up fix tickets are generated on the board (see Adversarial Dynamics). The orchestrator dispatches these before proceeding.
8. When all tickets in a milestone are `done`, the orchestrator validates the milestone, notifies the user with a brief status update, and unblocks the next milestone
9. Repeats until all milestones are complete or an escalation is needed

### Spec-First Workflow

Nothing happens without an agreed contract. Every task that goes through Split gets a spec phase. The spec scales with the task — a one-liner for straightforward work, a structured document for complex work — but it always exists.

**Flow:**

1. User invokes `/split` (or Claude auto-invokes it)
2. Orchestration skill activates, dispatches SME agent
3. SME agent has a conversation with the user — asks clarifying questions, understands intent, surfaces edge cases. The user interacts with the SME through the main session (the skill relays messages).
4. SME drafts a spec and writes it to `.claude/split/active/SXXX/spec.md`
5. Skill dispatches Tech Lead agent to review the spec internally — checks feasibility against the current codebase and architecture
6. If the Tech Lead has concerns, the skill surfaces them to the user (and to the SME for spec revision)
7. This loop continues until the Tech Lead is satisfied
8. Final spec is presented to the user for approval
9. Orchestration skill creates tickets from the approved spec
10. Execution begins (the skill walks the board as described above)

The user talks to the SME like talking to a consultant. The Tech Lead is the internal check who never lets an unrealistic spec through. The user sees the final result — a spec that's both domain-correct AND feasible.

### Complexity Classification

Once the `/split` skill is invoked, it classifies the task to determine the appropriate level of structure:

- **Medium** — 2-3 tickets, a few personas. Spec covers scope and approach. No milestones — tickets execute as a flat list.
- **Complex** — Multiple personas, dependencies between tickets, structured spec covering scope, approach, boundaries, and constraints. Tickets are grouped into **milestones** — meaningful checkpoints where accumulated work is validated before proceeding.

### Ticket Creation

After spec approval, the orchestrator creates tickets on the kanban board. For complex tasks, tickets are grouped into milestones:

```yaml
complexity: complex
milestones:
  - id: M001
    title: "Rate limiting design & core implementation"
    tickets:
      - id: T001
        title: "Design rate limiting approach"
        persona: tech-lead
        status: backlog
        depends_on: []
        acceptance_criteria: "Approach doc covering algorithm, limits, storage"
        produces: approach-doc

      - id: T002
        title: "Write tests for rate limiting middleware"
        persona: test-writer
        status: blocked
        depends_on: [T001]
        acceptance_criteria: "Tests covering normal flow, edge cases, error conditions"
        produces: tests

      - id: T003
        title: "Implement rate limiting middleware"
        persona: senior-dev
        status: blocked
        depends_on: [T002]
        acceptance_criteria: "Working implementation, all tests green"
        produces: implementation

      - id: T004
        title: "Code quality review of rate limiting"
        persona: code-reviewer
        status: blocked
        depends_on: [T003]
        acceptance_criteria: "Review covering patterns, maintainability, readability"
        produces: review-notes

      - id: T005
        title: "Verify rate limiting spec compliance"
        persona: tech-lead
        status: blocked
        depends_on: [T003]
        acceptance_criteria: "Implementation matches spec, architecture is sound"
        produces: review-notes

      - id: T006
        title: "Final verification of core implementation"
        persona: verifier
        status: blocked
        depends_on: [T004, T005]
        acceptance_criteria: "All tests pass, acceptance criteria met, edge cases covered"
        produces: verification-report

  - id: M002
    title: "Integration & hardening"
    tickets:
      - id: T007
        title: "Add rate limit headers and client documentation"
        persona: senior-dev
        status: blocked
        depends_on: [T003]
        acceptance_criteria: "Standard rate limit headers, error responses, docs"
        produces: implementation

      - id: T008
        title: "End-to-end verification"
        persona: verifier
        status: blocked
        depends_on: [T007]
        acceptance_criteria: "Full flow test including edge cases from M001 review"
        produces: verification-report
```

**The `produces` field** describes what kind of artifact the ticket outputs. This is freeform text — common values include `approach-doc`, `implementation`, `review-notes`, `threat-model`, `wireframes`, `documentation`. It tells downstream tickets and the retro what to expect from the ticket's output.

For medium-complexity tasks, there are no milestones — tickets are a flat list under a top-level `tickets` key (same format as the individual ticket objects above).

### Milestones

Milestones group tickets into sequential, reviewable chunks. They compartmentalize complex work so that each phase produces a coherent, understandable unit of change — rather than one long stream of 20 tickets where it's hard to see the shape of what's being built.

The execution engine processes milestones in order: all tickets in milestone N must be `done` before any ticket in milestone N+1 starts. Within a milestone, tickets with no dependencies between each other can be dispatched in parallel.

**Rules:**

- When a milestone's last ticket completes, the orchestrator validates: are the milestone's deliverables coherent? Does the accumulated work still align with the spec?
- If milestone validation surfaces issues, the orchestrator creates **follow-up tickets** in the current milestone (not a new one) to address them before moving to the next milestone

## Adversarial Dynamics

Personas don't rubber-stamp each other. Each one has skin in the game. When they clash, that's the system working.

### Spec Challenge (SME -> Tech Lead)

After the SME drafts the spec, the Tech Lead reviews it adversarially from a system constraints perspective. "Can we actually do this given what we have? Does this conflict with existing architecture? Is this scope realistic?" The challenged spec — not the original — is what the user approves.

### Test-First Workflow (Test Writer + Senior Dev)

For code tickets, the default flow is test-first: the Test Writer writes tests from the acceptance criteria before implementation begins, and the Senior Dev implements to satisfy the requirements.

**Key principle:** Tests describe how the system *should behave*. They verify behavior and describe a system state, not the change that was made. Having an independent persona write tests brings the "what should this do?" perspective, separate from the "how do I build this?" perspective of the implementer.

**Flow:**

1. Test Writer writes tests from acceptance criteria
2. Senior Dev reviews the tests — are they correct? comprehensive? testing behavior rather than implementation details?
3. Senior Dev implements. The goal is to implement what the requirements ask for correctly. Tests going green is *evidence* of correctness, not the objective.
4. If tests don't go green after implementation, the Senior Dev debugs systematically (see Systematic Debugging).

**Practical flexibility:** This is the default flow, not an absolute rule. Sometimes the interface only becomes clear during implementation, or the Test Writer can't write meaningful tests without more context about how the system will work. In those cases:

- The Senior Dev can adjust or extend tests as the interface evolves during implementation — they are not forbidden from touching test files.
- For tickets where the Test Writer can't work without more interface context, the Senior Dev may implement first, and the Test Writer writes independent verification tests afterward.
- The invariant is: tests should always benefit from independent thinking about what correct behavior looks like. Whether that happens before or after implementation depends on the situation.

### Code Quality Review (Code Reviewer)

After implementation passes tests, the Code Reviewer reviews the code for quality, patterns, and maintainability. This is a separate concern from spec compliance — it's about whether the code is *well-built*, not whether it does the right thing.

- Findings are categorized as **blockers** (must fix) or **suggestions** (optional improvements)
- **Blockers** generate follow-up fix tickets assigned to the Senior Dev, with specific concerns and acceptance criteria. The original dev ticket stays `done` — the fix is new scoped work.
- **Suggestions** are recorded as notes — available for the dev or retro to review, but they don't block progress.
- Follow-up fix tickets go through their own review. To prevent infinite loops, a fix ticket can generate at most one further follow-up. After that, unresolved issues escalate to the user.

### Spec Compliance Review (Tech Lead)

After the Code Reviewer passes, the Tech Lead checks: "Does this implementation match what the spec asked for? Are all requirements addressed? Does it fit the architecture?" This is separate from code quality — it's about correctness against the contract.

### Verification (Verifier)

The Verifier is the final gate. For every ticket — code or non-code — the Verifier confirms acceptance criteria are met and artifacts are correct. The Verifier adapts their approach based on ticket type:

| Ticket Type | Verification Approach |
|---|---|
| **Implementation** | Run tests, check acceptance criteria, test edge cases |
| **Documentation** | Accuracy check against code, completeness, clarity |
| **Design/Approach** | Feasibility check, coverage of requirements, risk identification |
| **Research** | Sources cited, conclusions supported, actionable findings |
| **Threat Model** | Coverage of attack vectors, mitigations specified, nothing hand-waved |
| **UX Wireframes** | User flow completeness, accessibility, consistency with existing patterns |

### Systematic Debugging

When tests fail or the Verifier finds issues, the Senior Dev follows a systematic methodology. This is a general approach, not a rigid checklist — the dev adapts to the situation:

- **Investigate** — Read code, reproduce the issue, gather evidence. Understand what's actually happening before guessing.
- **Write debugging tools** — This is critical. LLMs are excellent at writing and parsing logs. The dev should liberally add logging, write reproduction scripts, create test harnesses — whatever helps isolate the issue. Instrument first, then diagnose.
- **Hypothesize** — Form possible root causes. Don't jump to the first idea.
- **Test** — Verify or eliminate hypotheses using the instrumentation.
- **Fix** — Address the specific root cause, not symptoms. Write a regression test for the fix. Clean up debugging instrumentation.

### Approval Gates

Some tickets produce output that should not proceed without explicit user sign-off. A ticket with `requires_approval: true` enters `pending_approval` status when the persona completes it, instead of moving directly to `done`.

**When to use approval gates:**

- Security-sensitive changes (auth, data handling, permissions)
- Infrastructure or deployment changes
- Destructive operations (migrations, data deletion)
- Any ticket the orchestrator or Tech Lead flags as high-risk during ticket creation

**How it works:**

1. The persona-agent completes its work and produces artifacts as normal
2. The orchestration skill sets the ticket to `pending_approval` instead of `done`
3. Downstream tickets that depend on it remain blocked
4. The skill surfaces the output to the user: "Security Reviewer (T006) completed threat model. Review artifacts before proceeding? [approve / reject with feedback]"
5. **Approved** — ticket moves to `done`, downstream tickets unblock
6. **Rejected** — the skill re-dispatches to the same persona with the user's feedback. The ticket returns to `in_progress`. This loop continues until approved.

The SME can also recommend approval gates during the spec phase — if the user expresses concern about a particular area, the SME flags it and the orchestrator adds `requires_approval: true` to the relevant tickets.

### Escalation Path

If a fix ticket's own review generates yet another follow-up (two levels deep), or if personas fundamentally disagree on whether something is a blocker:

1. **Escalate to user** with both positions clearly summarized — "Code Reviewer says X, Senior Dev says Y. Your call."

The user is the ultimate tiebreaker. A third mediator agent could be experimented with in the future (the retro mechanism will surface whether escalations are too frequent), but for v1, the user decides.

### User Touchpoints

The system is designed to run for hours unattended. The user is the client, not a participant in every step. The spec phase front-loads user interaction — comprehensive questions, edge cases, constraints — so that execution can proceed autonomously.

The user's touchpoints are:

1. **Spec approval** — once, at the start. The user approves the challenged spec. The spec phase is thorough and asks the hard questions upfront, precisely so execution doesn't need to stop and wait.
2. **Approval gates** — only for explicitly flagged high-risk tickets (security, destructive ops, infra). Most tickets do NOT have this.
3. **Persona questions** — any persona can surface questions when they hit genuine ambiguity. These are ad-hoc, not a gate on every ticket.
4. **Demo** — at the end, the team walks the user through deliverables (see Demo below).
5. **Git decision** — the user decides what to do with the finished branch.

Everything else runs autonomously. Milestone completions do not pause for user confirmation — the orchestrator proceeds to the next milestone immediately. The only things that stop execution are approval gates and persona questions that genuinely cannot be resolved without user input.

### Demo

When all milestones are complete, the orchestrator runs a brief demo before the git decision. The team walks the user through what was delivered and how it works — similar to a sprint demo in a real company.

The demo focuses on what was delivered and how it works. The user is a developer, so walking through the implementation is valuable — key files changed, how the pieces fit together, notable decisions made during execution. If the work produced visible changes (UI, API endpoints, CLI output), those are shown. The user should come away understanding both what they got and how it's built.

## User Questions & Interaction

### Core Principle: Ask Early and Often

Every persona errs on the side of asking the user rather than assuming. The biggest problems come from assumptions that were never checked.

- **No guessing on ambiguity** — If the spec doesn't explicitly cover something, the persona asks. They don't infer, assume, or "use best judgment."
- **Preferences are always asked, never assumed** — "Should this be a modal or a new page?" is always a question, even if one option seems obviously better.
- **Confirm before irreversible decisions** — Even if the spec says one thing, if the persona sees a viable alternative, surface it.
- **Batch when possible, but don't hold back** — Multiple questions at once are fine. Delaying a question hoping the answer will become clear is not.

### Direct Persona-to-User Communication

Any persona can surface questions directly to the user. There is no relay through the SME — when the Security Reviewer has a question, the user hears from the Security Reviewer. The orchestration skill passes questions through tagged with the persona's identity and ticket ID, preserving the original phrasing.

### Escalation Hierarchy

Before asking the user, personas try to resolve internally:

1. **Check the spec** — the answer might already be there
2. **Ask another persona internally** — UX Designer unsure about a technical constraint? Ask the Tech Lead. Dev unsure about intended behavior? Ask the SME.
3. **If no internal persona can answer** — Escalate to the user

### Question Format

Questions are always tagged with persona and ticket for context, and present options with a recommendation:

```
UX Designer (T004) has a question:

The spec doesn't specify how settings should be organized.
  A: Grouped by category (Privacy, Notifications, Account)
  B: Flat searchable list
I'd recommend A for discoverability. Your preference?
```

Answers are recorded on the ticket as decisions, so other personas and the retro can reference them.

## The Kanban Board

### Structure: One Board Per Spec

Each spec gets its own directory with its own board. This prevents unbounded growth and keeps context focused.

```
.claude/split/
├── active/                       # Current work (multiple specs can be active)
│   ├── S001/
│   │   ├── spec.md               # The approved spec
│   │   ├── board.yaml            # Tickets for this spec only
│   │   ├── metrics.yaml          # Token usage, progress counters
│   │   ├── log.md                # Append-only execution log
│   │   └── artifacts/            # Output from each ticket
│   └── S002/                 # Parallel spec (if active)
│       ├── spec.md
│       ├── board.yaml
│       ├── metrics.yaml
│       ├── log.md
│       └── artifacts/
├── archive/                      # Completed work
│   └── SXXX/
│       ├── spec.md
│       ├── board.yaml
│       ├── metrics.yaml
│       ├── log.md
│       ├── artifacts/
│       └── retro.md              # Retro notes for this spec
```

### Board File Format

```yaml
spec: S001
title: "Add rate limiting to API endpoints"
created: 2026-04-10T10:30:00Z
status: active  # active | completed | archived

milestones:
  - id: M001
    title: "Rate limiting design & core implementation"
    status: active
    tickets:
      - id: T001
        title: "Design rate limiting approach"
        persona: tech-lead
        status: done
        depends_on: []
        acceptance_criteria: "Approach doc covering algorithm, limits, storage"
        produces: approach-doc
        tokens_used: 18200
        artifacts:
          - artifacts/T001-approach.md

      - id: T002
        title: "Write tests for rate limiting middleware"
        persona: test-writer
        status: done
        depends_on: [T001]
        acceptance_criteria: "Tests covering normal flow, edge cases, error conditions"
        produces: tests
        tokens_used: 15300
        artifacts:
          - tests/middleware/rate-limiter.test.ts

      - id: T003
        title: "Implement rate limiting middleware"
        persona: senior-dev
        status: done
        depends_on: [T002]
        acceptance_criteria: "Working implementation, all tests green"
        produces: implementation
        tokens_used: 42500
        artifacts:
          - src/middleware/rate-limiter.ts

      - id: T004
        title: "Code quality review of rate limiting"
        persona: code-reviewer
        status: done
        depends_on: [T003]
        acceptance_criteria: "Review covering patterns, maintainability, readability"
        produces: review-notes
        tokens_used: 18700
        artifacts:
          - artifacts/T004-review.md
        follow_ups: [T004a]

      - id: T004a
        title: "Fix race condition on concurrent requests"
        persona: senior-dev
        status: in_progress
        depends_on: [T004]
        created_by: T004  # tracks which review spawned this
        acceptance_criteria: "Mutex on counter increment, verified under concurrent load"
        produces: implementation
        tokens_used: 0
        artifacts: []

      - id: T005
        title: "Verify rate limiting spec compliance"
        persona: tech-lead
        status: blocked
        depends_on: [T003]
        acceptance_criteria: "Implementation matches spec, architecture is sound"
        produces: review-notes
        tokens_used: 0
        artifacts: []

      - id: T006
        title: "Final verification of core implementation"
        persona: verifier
        status: blocked
        depends_on: [T004a, T005]
        acceptance_criteria: "All tests pass, acceptance criteria met, edge cases covered"
        produces: verification-report
        tokens_used: 0
        artifacts: []

  - id: M002
    title: "Integration & hardening"
    status: blocked
    tickets:
      - id: T007
        title: "Add rate limit headers and error responses"
        persona: senior-dev
        status: blocked
        depends_on: [T003]
        acceptance_criteria: "Standard headers, documented error format"
        produces: implementation
        tokens_used: 0
        artifacts: []

decisions:
  - ticket: T003
    question: "Redis or in-memory for rate limit storage?"
    answered_by: user
    answer: "Redis — we need this to work across multiple instances"
    date: 2026-04-10T11:15:00Z
```

The companion `metrics.yaml` for this board:

```yaml
spec: S001
started: 2026-04-10T10:30:00Z
agent_dispatches: 7
total_tickets: 8
completed_tickets: 4
follow_up_tickets: 1
user_questions: 2
milestones_completed: 0
total_tokens: 94700
```

Metrics live in a separate `metrics.yaml` file in the same spec directory, not in the board. Personas read the board for tickets and dependencies; the retro engine and CLI dashboard read `metrics.yaml`. The orchestration skill updates `metrics.yaml` after every ticket state change and commits it alongside the board. `total_tokens` is the sum of all `tokens_used` across tickets — the orchestrator records each persona-agent's token consumption when it completes.

Decisions live at the board level, not inside individual tickets. A single decision can affect multiple tickets (e.g., "use Redis" spans implementation, testing, and documentation), so the board maintains one canonical decisions list. Personas and the retro engine look up decisions from this list, not from scattered ticket fields.

### Lifecycle

- **Active:** spec is being worked on, tickets are in progress
- **Completed:** all tickets done, ready for archive
- **Archived:** moved to `archive/` directory, retro completed

The orchestrator discovers active specs by scanning the `active/` directory — each subdirectory is a spec. No separate manifest is needed; the folder structure is the source of truth. Archived specs are available for retros and for personas to reference past decisions.

### Context Window Efficiency

The orchestrator and personas only load the board for the spec they're working on. Archived work doesn't consume tokens unless explicitly referenced.

### Board State Versioning

The board file is version-controlled through git. The orchestration skill commits the board after every state change (ticket completion, status update, follow-up creation). This provides:

- Full history of every state transition via `git log`
- Recovery from any corruption by reverting to a previous commit
- Perfect audit trail for the retro engine
- No risk of losing state — git handles the durability

Commits are small (single YAML file) and cheap. If the commit history gets noisy, it can be squashed when the spec is archived.

### Execution Log

Each spec has an append-only `log.md` that records every significant event during execution. The orchestration skill appends to this file after each action. The log is invaluable for retrospective debugging — understanding *why* something went wrong, not just *what* the final state is.

**What gets logged:**

- Ticket dispatches (which persona, which ticket, timestamp)
- Ticket completions (outcome, tokens used, artifacts produced)
- Review findings (blockers and suggestions, with ticket references)
- Follow-up ticket creation (what triggered it, assigned to whom)
- User questions asked and answers received
- Decisions made (by personas internally or by the user)
- Errors and retries (what failed, what was retried, outcome)
- Milestone completions and validations
- Spec amendments and their scope
- Approval gate outcomes (approved, rejected with reason)

**Format:**

```markdown
## S001 Execution Log

### 2026-04-10T10:32:00Z — Ticket dispatched
T001 -> tech-lead | Design rate limiting approach

### 2026-04-10T10:38:00Z — Ticket completed
T001 -> tech-lead | done | 18,200 tokens
Artifacts: artifacts/T001-approach.md

### 2026-04-10T10:38:30Z — Ticket dispatched
T002 -> test-writer | Write tests for rate limiting middleware

### 2026-04-10T10:43:00Z — Ticket completed
T002 -> test-writer | done | 15,300 tokens
Artifacts: tests/middleware/rate-limiter.test.ts

### 2026-04-10T10:43:30Z — Ticket dispatched
T003 -> senior-dev | Implement rate limiting middleware

### 2026-04-10T10:50:00Z — User question
T003 -> senior-dev | "Redis or in-memory for rate limit storage?"
Answer (user): "Redis — we need this to work across multiple instances"

### 2026-04-10T10:57:00Z — Ticket completed
T003 -> senior-dev | done | 42,500 tokens
Artifacts: src/middleware/rate-limiter.ts

### 2026-04-10T10:58:00Z — Code quality review
T004 -> code-reviewer | Blockers: 1 (race condition on concurrent requests)
Follow-up created: T004a -> senior-dev
```

The log is append-only — entries are never modified or deleted. The retro engine reads it alongside the board and artifacts for a complete picture of how execution unfolded.

## The Retro Engine

At session end, the team holds a retrospective.

### What the Retro Does

1. **Reviews completed specs** — reads the archived spec, board, artifacts, and decisions
2. **Evaluates persona performance** — Did the Tech Lead catch the right issues? Did the Code Reviewer find real problems or just nitpick? Did the dev address feedback well? Did anyone make assumptions they should have asked about?
3. **Identifies patterns** — "Code Reviewer keeps finding the same type of issue in auth code" or "the spec phase missed edge cases that the Verifier caught later"
4. **Proposes persona updates** — Concrete changes to persona markdown files
5. **Proposes workflow updates** — Observations about the process itself, including updates to project-level configuration (e.g., CLAUDE.md, AGENTS.md) when patterns reflect project-wide preferences rather than persona-specific behavior

### Retro Output Format

```markdown
# Retro: S001 — Rate Limiting

## What went well
- Tech Lead caught that we needed Redis vs in-memory early
- Code Reviewer found the race condition on concurrent requests

## What could improve
- Spec didn't mention backwards compatibility for existing clients
- Dev/Code Reviewer went 3 rounds on error response format (cosmetic, not functional)

## Proposed persona updates
1. **SME** — Add: "For API changes, always clarify backwards compatibility
   requirements with the user"
2. **Code Reviewer** — Add: "Distinguish between functional issues (must fix)
   and style issues (suggest, don't block)"

## Proposed workflow observations
- Consider adding a dev self-review checklist before passing to Code Reviewer
  to reduce cosmetic round-trips
```

### Human Approval

The retro produces proposed changes, not automatic edits. The user reviews each proposed persona update and approves, modifies, or rejects. The system learns, but the human controls the direction.

### Trigger

- **Automatic:** the orchestrator runs a retro when a spec is completed and archived

## Dashboard

The primary dashboard is a CLI TUI (see the [Split Board CLI spec](2026-04-11-split-board-cli-design.md)). A browser-based HTML dashboard that renders `board.yaml` as a visual kanban board is a future improvement — the board format supports it without any structural changes, so it can be added later without affecting the orchestrator or CLI.

## Execution Flow — End to End

Every `/split` invocation creates a git worktree (`split/SXXX` branch). All work happens in the worktree, isolated from the user's working directory.

### Medium Task

Example: "add rate limiting to the API"

```
User invokes /split (or Claude auto-invokes)
  → Orchestration skill activates
  → Git worktree created (branch: split/S001)

SPEC PHASE:
  → SME asks clarifying questions
    (which endpoints? what limits? authenticated vs anonymous?)
  → SME drafts spec
  → Tech Lead reviews internally
    ("we don't have Redis — in-memory or add a dependency?")
  → Back and forth until Tech Lead is satisfied
  → Final spec presented to User → approved

TICKET CREATION:
  → Orchestrator creates board (flat list, no milestones):
    T001: Tech Lead — design approach [backlog]
    T002: Test Writer — write tests [blocked by T001]
    T003: Senior Dev — implement [blocked by T002]
    T004: Code Reviewer — review quality [blocked by T003]
    T005: Verifier — final verification [blocked by T004]

EXECUTION:
  → T001: Tech Lead produces approach doc → done
  → T002: Test Writer writes tests from acceptance criteria → done
  → T003: Senior Dev reviews tests, implements → all tests green → done
  → T004: Code Reviewer reviews quality → no blockers → done
  → T005: Verifier confirms acceptance criteria met → done
  → All tickets done

DEMO:
  → Team walks user through: what was delivered, how it works,
    key files changed, notable decisions

GIT DECISION:
  → Worktree branch merged back to user's branch
  → User decides: merge to main / create PR / keep branch

ARCHIVE:
  → Spec directory moves to archive/
  → Retro suggested if enough specs accumulated
```

### Complex Task

Example: "add rate limiting to the API" (larger scope with milestones)

```
User invokes /split
  → Orchestration skill activates
  → Git worktree created (branch: split/S001)

SPEC PHASE:
  → SME asks clarifying questions
    (which endpoints? what limits? authenticated vs anonymous?)
  → SME drafts spec
  → Tech Lead reviews internally
    ("we don't have Redis — in-memory or add a dependency?")
  → Back and forth until Tech Lead is satisfied
  → Final spec presented to User → approved

TICKET CREATION:
  → Orchestrator creates board with milestones:
    M001: "Design & core implementation"
      T001: Tech Lead — design approach [backlog]
      T002: Test Writer — write tests [blocked by T001]
      T003: Senior Dev — implement [blocked by T002]
      T004: Code Reviewer — review quality [blocked by T003]
      T005: Tech Lead — spec compliance [blocked by T003]
      T006: Verifier — final verification [blocked by T004, T005]
    M002: "Integration & hardening"
      T007: Senior Dev — headers & docs [blocked by M001]
      T008: Verifier — end-to-end verification [blocked by T007]

EXECUTION — M001:
  → T001: Tech Lead produces approach doc → done
  → T002: Test Writer writes tests → done
  → T003: Senior Dev reviews tests, implements → done
  → T004: Code Reviewer reviews quality
    → Finds race condition → creates follow-up T004a
  → T004a: Senior Dev fixes race condition → done
  → T005: Tech Lead confirms spec compliance → done
  → T006: Verifier runs final checks → all pass → done
  → M001 complete — orchestrator validates, notifies user
  → User confirms: "looks good, proceed"

EXECUTION — M002:
  → T007: Senior Dev adds headers and docs → done
  → T008: Verifier end-to-end verification → pass → done
  → M002 complete — all milestones done

DEMO:
  → Team walks user through deliverables, implementation,
    key decisions made during execution

GIT DECISION:
  → Worktree branch merged back to user's branch
  → User decides: merge to main / create PR / keep branch

ARCHIVE:
  → Spec directory moves to archive/
  → Retro suggested if enough specs accumulated
```

### Multi-Persona Complex Task

Example: "redesign the settings page with better security"

```
  → Orchestrator pulls in: SME, Tech Lead, UX Designer,
    Senior Dev, Security Reviewer, Test Writer, Code Reviewer, Verifier
  → Tickets:
    - UX Designer: propose layout and interaction flow
    - Security Reviewer: audit auth/data exposure in current page [requires_approval]
    - Tech Lead: approach doc incorporating UX and security inputs
    - Test Writer: write tests from approach doc
    - Senior Dev: implement
    - Code Reviewer: review code quality
    - Tech Lead: verify spec compliance
    - Verifier: final verification
```

### What the User Experiences

They invoke `/split` (or Claude recognizes the task warrants it). A worktree is created automatically. They have a conversation with the SME to nail down what they want. They see a spec and approve it. Work happens autonomously — they're only interrupted for approval gates on high-risk tickets, milestone checkpoints, and genuine questions from personas. At the end, the team demos what was delivered and how it works. They decide what to do with the branch.

## Error Handling & Recovery

### Parallel Specs

Multiple specs can be active simultaneously. Each spec has its own board, log, artifacts directory, and git worktree. Since every `/split` invocation creates its own worktree, parallel specs are naturally isolated — each works on its own branch in its own directory. The orchestrator discovers them by scanning the `active/` directory. It is ultimately the user's responsibility to manage whether parallel specs are safe to merge concurrently.

### Agent Failure Mid-Ticket

When a persona-agent fails (context limit, tool error, or produces clearly wrong output):

1. The orchestration skill marks the ticket as `failed` with the error details
2. The skill reports the failure to the user: "Senior Dev failed on T002: [reason]. Options: retry, reassign, or skip."
3. **Retry** — re-dispatches the same ticket to the same persona with a fresh context window. The previous attempt's error is included as context so the agent can avoid the same mistake.
4. **Reassign** — the user can assign the ticket to a different persona (e.g., if the Senior Dev hit a context limit on a large file, the user might split the ticket).
5. **Skip** — mark the ticket as `skipped`. Downstream tickets that depend on it are also marked `blocked_by_skip` and the user is informed.

### Board Corruption

The board file is YAML and version-controlled through git. If it fails to parse:

1. The orchestration skill checks `git log` for the last valid commit of `board.yaml`
2. Reverts to the last good state with `git checkout <commit> -- board.yaml`
3. Informs the user what was lost (typically just the last state update)

Since the board is committed after every state change, at most one transition is lost.

### Abandoning a Spec

The user can say "abandon this" or "cancel" at any point:

1. The orchestration skill stops dispatching tickets
2. Any in-progress agent is allowed to complete its current turn (no forceful interruption)
3. The spec directory is moved to `archive/` with `status: abandoned`
4. The retro can still review abandoned specs — sometimes the most useful lessons come from work that was stopped

### Amending a Spec Mid-Execution

If the user wants to change requirements after tickets are in progress:

1. The orchestration skill pauses execution (no new tickets dispatched)
2. The SME re-engages with the user to understand the change
3. The Tech Lead reviews the amendment against work already completed
4. Options presented to the user:
   - **Minor amendment** — update the spec, adjust only affected tickets. Completed tickets that are still valid keep their `done` status.
   - **Major amendment** — the scope has changed enough that completed work may be invalid. The orchestrator flags which tickets need re-evaluation and the user decides which to redo.
5. Board is updated, execution resumes

### Misclassification

If the orchestrator gets the complexity wrong (e.g., classifies a large feature as medium when it should be complex):

- The persona working the task can escalate: "This is more complex than a flat ticket list. I need milestones."
- The orchestration skill re-classifies and restructures the board
- The work done so far isn't lost — completed tickets carry over into the restructured board

### Session Resumption

The board file *is* the state. When a user starts a new session with an active spec:

1. The user invokes `/split` (or Claude auto-invokes it upon recognizing context relevant to an active spec)
2. The orchestration skill scans the `active/` directory for spec subdirectories
3. Loads the board, identifies the current state (which tickets are done, in progress, or blocked), and resumes execution from the next unblocked ticket
4. If a ticket was `in_progress` when the previous session ended, the orchestrator re-dispatches it — the persona-agent gets a fresh context window with the ticket's acceptance criteria, spec reference, and any artifacts from completed dependencies. The previous partial work (if any) is noted but not relied upon.

The user sees a summary on resumption:

```
Resuming S001: Add rate limiting to API endpoints
  M001: 3/4 tickets done
  Next: T003a (Senior Dev — fix race condition)
  Continue? [y/n]
```

No special mechanism is needed beyond what the board already provides — the board is the checkpoint.

## File Structure & Distribution

### Plugin Structure

```
split/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── agents/                       # Persona definitions
│   ├── sme/sme.md
│   ├── tech-lead/tech-lead.md
│   ├── senior-dev/senior-dev.md
│   ├── test-writer/test-writer.md
│   ├── code-reviewer/code-reviewer.md
│   ├── verifier/verifier.md
│   ├── researcher/researcher.md
│   ├── ux-designer/ux-designer.md
│   ├── devops/devops.md
│   ├── security-reviewer/security-reviewer.md
│   └── technical-writer/technical-writer.md
├── skills/
│   ├── split/SKILL.md           # Main orchestrator skill
│   ├── retro/SKILL.md           # Retrospective skill
│   └── status/SKILL.md          # Board status & progress view
└── settings.json                 # Default plugin settings
```

### Installation

```
claude plugin install split@<marketplace>
```

User gets the full team, orchestrator, and retro engine immediately.

### Portability

The persona definitions are plain markdown with YAML frontmatter — trivially convertible to system prompts on any platform. The orchestration prompt is plain text. Only the agent-dispatch layer is Claude Code specific, forming a thin adapter that can be replicated for other systems.

## Open Questions for Future Iteration

- **Mediator agent for tiebreaking:** Could a third agent (pragmatic engineering manager) resolve persona disagreements before escalating to the user? The retro will surface whether this is needed based on escalation frequency.
- **Persona self-proposal:** Could personas propose updates to their own definitions during work (not just during retros)? "I keep needing to ask about encoding — I should add that to my checklist."
- **Computer use for verification:** If Claude Code supports computer use or screenshot tools, the Verifier could launch the app, navigate user flows, and verify UI changes visually — runtime verification beyond code review.
