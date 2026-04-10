# Split AI — Design Spec

A Claude Code plugin that turns a single AI session into a team of specialized personas, coordinated by an LLM-powered orchestrator through a kanban board system.

Inspired by the movie *Split* — but instead of personalities competing for control, this is a professional team where each member has their own role, objectives, and accountability, all working together on the same project.

## Core Concepts

Split has four pillars:

1. **Personas** — Markdown-defined Claude Code agents, each with a role, objectives, what they optimize for, and persistent memory. Ships with a default team; users extend by adding markdown files.

2. **Orchestrator** — An LLM-powered classifier that intercepts every user prompt. It drives a spec-first workflow: the user talks to a Subject Matter Expert, the spec is reviewed internally by the Tech Lead, then the orchestrator creates tickets on the kanban board.

3. **Kanban Board** — A file-based board tracking all work. Each spec gets its own board. Tickets have assigned personas, dependencies, acceptance criteria, and artifact references. An execution engine walks the board, dispatching unblocked tickets to persona-agents.

4. **Retro Engine** — At session end (user-triggered), the team reviews what happened: what worked, what didn't, and proposes updates to persona definitions. The human approves all changes.

## Personas

Each persona is a Claude Code custom agent defined in `agents/<persona-name>/<persona-name>.md`. This gives each persona its own full system prompt (strongest behavioral shaping) and persistent memory.

### Persona Definition Structure

```yaml
---
name: tech-lead
description: Architectural decisions, approach design, trade-off analysis
memory: project
model: opus
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

Every persona includes the "Core Operating Principle" section above — the mandate to ask rather than assume.

### Default Team

| Persona | Role | Optimizes For | When Activated |
|---------|------|---------------|----------------|
| **SME** | Domain expert, user-facing dialogue, spec drafting | Correctly capturing user intent | Every task (user-facing) |
| **Tech Lead** | Feasibility, architecture, system constraints | Specs that are achievable in the current codebase | Every spec (internal review) |
| **Senior Dev** | Implementation | Clean, correct, idiomatic code | Code changes |
| **QA** | Adversarial review, actively tries to break things | Catching bugs, pragmatically — good enough, not perfect | After implementation |
| **Researcher** | Deep investigation — legal, compliance, market analysis, technical feasibility | Thorough, well-sourced findings | Knowledge gathering before decisions |
| **UX Designer** | UI/UX patterns, accessibility, user flows, interaction design | Usable, consistent interfaces | Any user-facing interface work |
| **DevOps** | Infrastructure, CI/CD, deployment, monitoring, performance | Reliable, observable systems | Infra changes, deployment, performance |
| **Security Reviewer** | Threat modeling, vulnerability analysis, auth/authz | Secure by default | Security-sensitive changes, auth, data handling |
| **Technical Writer** | Documentation, API docs, user guides, changelog | Clear, accurate, maintainable docs | When deliverables include documentation |

### Extension

Users add personas by dropping a markdown file in their project's `.claude/agents/` directory. The orchestrator automatically discovers available personas from the agents directory. A fintech team might add a Compliance Officer; a gamedev team might add a Game Designer.

Users can override a default persona by creating one with the same name in their project — project-level agents take priority over plugin agents.

### Memory

Each persona uses Claude Code's built-in agent memory (`memory: project`). Memory is scoped to the project, persists across sessions, and evolves naturally:

- The Tech Lead remembers past architectural decisions
- QA remembers which areas tend to have bugs
- The SME remembers domain-specific context from prior conversations

Memory is curated through the retro process — the retro can propose additions to persona memory, not just their system prompts.

## The Orchestrator

The orchestrator is the brain of Split. It intercepts every user prompt and drives the spec-first workflow.

### Mechanism — Two Components

The orchestrator is split into two parts:

1. **Classification hook** — A `UserPromptSubmit` hook of type `prompt`. This is a single-turn LLM call (Opus) that analyzes the incoming prompt and returns a classification: complexity level, which personas are relevant, and whether this is new work or a continuation of an active spec. The classification is injected as `additionalContext` into the main session.

2. **Orchestration skill** (`/split`) — An auto-invoked skill that the main session activates based on the hook's classification. This skill drives the multi-turn workflow: dispatching to the SME agent for user conversation, passing the draft spec to the Tech Lead agent for internal review, creating the board, and driving execution through the ticket queue.

The hook is the fast classifier. The skill is the workflow engine.

### Execution Engine

The orchestration skill acts as the execution engine. After tickets are created, it:

1. Reads the board file to find unblocked tickets (all dependencies in `done` status)
2. Dispatches each unblocked ticket to its assigned persona via the Agent tool
3. The persona-agent receives the ticket context (acceptance criteria, spec reference, artifacts from dependency tickets) as its prompt
4. When the agent completes, the skill updates the board (status, artifacts)
5. If the persona-agent has questions for the user, it returns them — the skill surfaces these to the user and feeds the answers back
6. Repeats until all tickets are done or an escalation is needed

For the QA review loop specifically: when QA rejects, the skill moves the dev ticket back to `in_progress`, increments `review_rounds`, and re-dispatches to the dev with QA's rejection notes.

### Spec-First Workflow

Nothing happens without an agreed contract. Every task, regardless of complexity, goes through a spec phase. The spec scales with the task — a one-liner for trivial work, a structured document for complex work — but it always exists.

**Flow:**

1. User prompt arrives
2. Classification hook assesses complexity and relevant personas (single-turn, fast)
3. Orchestration skill activates, dispatches SME agent
4. SME agent has a conversation with the user — asks clarifying questions, understands intent, surfaces edge cases. The user interacts with the SME through the main session (the skill relays messages).
5. SME drafts a spec and writes it to `.claude/split/active/SPEC-XXX/spec.md`
6. Skill dispatches Tech Lead agent to review the spec internally — checks feasibility against the current codebase and architecture
7. If the Tech Lead has concerns, the skill relays them back to the SME (or surfaces questions to the user)
8. This loop continues until the Tech Lead is satisfied
9. Final spec is presented to the user for approval
10. Orchestration skill creates tickets from the approved spec
11. Execution begins (the skill walks the board as described above)

The user talks to the SME like talking to a consultant. The Tech Lead is the internal check who never lets an unrealistic spec through. The user sees the final result — a spec that's both domain-correct AND feasible.

### Complexity Classification

The orchestrator classifies each prompt to determine the appropriate level of structure:

- **Simple** — One persona, one ticket, brief spec ("Fix typo 'recieve' → 'receive' in utils.py:42"). Spec phase is quick but still happens.
- **Medium** — 2-3 tickets, a few personas. Spec covers scope and approach.
- **Complex** — Multiple personas, dependencies between tickets, structured spec covering scope, approach, boundaries, and constraints.

### Ticket Creation

After spec approval, the orchestrator creates tickets on the kanban board:

```yaml
complexity: high
tickets:
  - id: SPLIT-001
    title: "Design rate limiting approach"
    persona: tech-lead
    status: backlog
    depends_on: []
    acceptance_criteria: "Approach doc covering algorithm choice, per-endpoint limits, storage backend"
    produces: approach-doc

  - id: SPLIT-002
    title: "Implement rate limiting"
    persona: senior-dev
    status: blocked
    depends_on: [SPLIT-001]
    acceptance_criteria: "Working implementation following the approach doc"
    produces: implementation

  - id: SPLIT-003
    title: "Review rate limiting for edge cases"
    persona: qa
    status: blocked
    depends_on: [SPLIT-002]
    acceptance_criteria: "Review notes covering race conditions, bypass vectors, load behavior"
    produces: review-notes
```

The execution engine walks the board, picking up unblocked tickets and dispatching them to the assigned persona-agent.

## Adversarial Dynamics

Personas don't rubber-stamp each other. Each one has skin in the game. When they clash, that's the system working.

### Spec Challenge (SME → Tech Lead)

After the SME drafts the spec, the Tech Lead reviews it adversarially from a system constraints perspective. "Can we actually do this given what we have? Does this conflict with existing architecture? Is this scope realistic?" The challenged spec — not the original — is what the user approves.

### Work Review Loop (Dev → QA)

When a dev ticket moves to Done, the QA ticket unblocks. QA actively tries to break the implementation:

- If QA finds issues: ticket moves back from Done → In Progress, with specific rejection notes
- Dev must address the specific issues
- This can bounce back and forth up to 2-3 rounds
- QA is pragmatic — "good enough" is the bar, not "perfect." Perfect is the enemy of good. Functional issues must be fixed; style issues are suggestions, not blockers.

### Escalation Path

If after max rounds the dev and QA still disagree:

1. **Escalate to user** with both positions clearly summarized — "QA says X, Dev says Y. Your call."

The user is the ultimate tiebreaker. A third mediator agent could be experimented with in the future (the retro mechanism will surface whether escalations are too frequent), but for v1, the user decides.

## User Questions & Interaction

### Core Principle: Ask Early and Often

Every persona errs on the side of asking the user rather than assuming. The biggest problems come from assumptions that were never checked.

- **No guessing on ambiguity** — If the spec doesn't explicitly cover something, the persona asks. They don't infer, assume, or "use best judgment."
- **Preferences are always asked, never assumed** — "Should this be a modal or a new page?" is always a question, even if one option seems obviously better.
- **Confirm before irreversible decisions** — Even if the spec says one thing, if the persona sees a viable alternative, surface it.
- **Batch when possible, but don't hold back** — Multiple questions at once are fine. Delaying a question hoping the answer will become clear is not.

### Escalation Hierarchy

Before asking the user, personas try to resolve internally:

1. **Check the spec** — the answer might already be there
2. **Ask another persona internally** — UX Designer unsure about a technical constraint? Ask the Tech Lead. Dev unsure about intended behavior? Ask the SME.
3. **If no internal persona can answer** — Escalate to the user

### Question Format

Questions are always tagged with persona and ticket for context, and present options with a recommendation:

```
UX Designer (SPLIT-004) has a question:

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
├── active/                       # Current work
│   └── SPEC-XXX/
│       ├── spec.md               # The approved spec
│       ├── board.yaml            # Tickets for this spec only
│       └── artifacts/            # Output from each ticket
├── archive/                      # Completed work
│   └── SPEC-XXX/
│       ├── spec.md
│       ├── board.yaml
│       ├── artifacts/
│       └── retro.md              # Retro notes for this spec
└── index.yaml                    # Lightweight manifest of all specs
```

### Board File Format

```yaml
spec: SPEC-001
title: "Add rate limiting to API endpoints"
created: 2026-04-10T10:30:00Z
status: active  # active | completed | archived

tickets:
  - id: SPLIT-001
    title: "Design rate limiting approach"
    persona: tech-lead
    status: done
    depends_on: []
    acceptance_criteria: "Approach doc covering algorithm, limits, storage"
    artifacts:
      - artifacts/SPLIT-001-approach.md

  - id: SPLIT-002
    title: "Implement rate limiting middleware"
    persona: senior-dev
    status: review
    depends_on: [SPLIT-001]
    acceptance_criteria: "Working implementation per approach doc"
    review_rounds: 1
    max_rounds: 3
    artifacts:
      - src/middleware/rate-limiter.ts

  - id: SPLIT-003
    title: "Adversarial review of rate limiting"
    persona: qa
    status: in_progress
    depends_on: [SPLIT-002]
    acceptance_criteria: "Review covering race conditions, bypass vectors, load"
    artifacts: []

decisions:
  - ticket: SPLIT-002
    question: "Redis or in-memory for rate limit storage?"
    answered_by: user
    answer: "Redis — we need this to work across multiple instances"
    date: 2026-04-10T11:15:00Z
```

### Lifecycle

- **Active:** spec is being worked on, tickets are in progress
- **Completed:** all tickets done, ready for archive
- **Archived:** moved to `archive/` directory, retro completed

The `index.yaml` is a lightweight manifest — just spec IDs, titles, statuses, dates. The orchestrator reads this to know what's active without loading every board. Archived specs are available for retros and for personas to reference past decisions.

### Context Window Efficiency

The orchestrator and personas only load the board for the spec they're working on. Archived work doesn't consume tokens unless explicitly referenced.

## The Retro Engine

At session end or on demand via `/retro`, the team holds a retrospective.

### What the Retro Does

1. **Reviews completed specs** — reads the archived spec, board, artifacts, and decisions
2. **Evaluates persona performance** — Did the Tech Lead catch the right issues? Did QA find real problems or just nitpick? Did the dev address feedback well? Did anyone make assumptions they should have asked about?
3. **Identifies patterns** — "QA keeps finding the same type of issue in auth code" or "the spec phase missed edge cases that QA caught later"
4. **Proposes persona updates** — Concrete changes to persona markdown files
5. **Proposes workflow updates** — Observations about the process itself

### Retro Output Format

```markdown
# Retro: SPEC-001 — Rate Limiting

## What went well
- Tech Lead caught that we needed Redis vs in-memory early
- QA found the race condition on concurrent requests

## What could improve
- Spec didn't mention backwards compatibility for existing clients
- Dev/QA went 3 rounds on error response format (cosmetic, not functional)

## Proposed persona updates
1. **SME** — Add: "For API changes, always clarify backwards compatibility
   requirements with the user"
2. **QA** — Add: "Distinguish between functional issues (must fix) and
   style issues (suggest, don't block)"

## Proposed workflow observations
- Consider adding a dev self-review checklist before passing to QA
  to reduce cosmetic round-trips
```

### Human Approval

The retro produces proposed changes, not automatic edits. The user reviews each proposed persona update and approves, modifies, or rejects. The system learns, but the human controls the direction.

### Trigger

- **Manual:** user invokes `/retro`
- **Suggested:** when a configurable number of specs have been archived since the last retro

## Execution Flow — End to End

### Simple Task

Example: "fix the typo in utils.py"

```
User prompt
  → Orchestrator classifies: simple
  → SME confirms intent with user (brief)
  → Spec: "Fix typo 'recieve' → 'receive' in utils.py:42"
  → Tech Lead: "No concerns"
  → Single ticket → Senior Dev executes → Done
  → Archived
```

### Complex Task

Example: "add rate limiting to the API"

```
User prompt
  → Orchestrator classifies: complex

SPEC PHASE:
  → SME asks clarifying questions
    (which endpoints? what limits? authenticated vs anonymous?)
  → SME drafts spec
  → Tech Lead reviews internally
    ("we don't have Redis — in-memory or add a dependency?")
  → Back and forth until Tech Lead is satisfied
  → Final spec presented to User → approved

TICKET CREATION:
  → Orchestrator creates board:
    SPLIT-001: Tech Lead — design approach [backlog]
    SPLIT-002: Senior Dev — implement [blocked by 001]
    SPLIT-003: QA — adversarial review [blocked by 002]

EXECUTION:
  → SPLIT-001: Tech Lead produces approach doc → done
  → SPLIT-002: Senior Dev implements → moves to review
  → SPLIT-003: QA tries to break it
    → Finds race condition → ticket back to Senior Dev
    → Senior Dev fixes → back to QA
    → QA satisfied → done
  → All tickets done

ARCHIVE:
  → Spec directory moves to archive/
  → Retro suggested if enough specs accumulated
```

### Multi-Persona Complex Task

Example: "redesign the settings page with better security"

```
  → Orchestrator pulls in: SME, Tech Lead, UX Designer,
    Senior Dev, Security Reviewer, QA
  → Tickets:
    - UX Designer: propose layout and interaction flow
    - Security Reviewer: audit auth/data exposure in current page
    - Tech Lead: approach doc incorporating UX and security inputs
    - Senior Dev: implement
    - QA: adversarial review
```

### What the User Experiences

They type a prompt. They have a conversation with the SME to nail down what they want. They see a spec and approve it. They see a board with tickets. Work happens. Personas ask questions when they need human judgment. If there's a disagreement that can't be resolved, they're asked to weigh in. Otherwise, they get the finished result.

## File Structure & Distribution

### Plugin Structure

```
split-ai/
├── .claude-plugin/
│   └── plugin.json              # Plugin manifest
├── agents/                       # Persona definitions
│   ├── sme/sme.md
│   ├── tech-lead/tech-lead.md
│   ├── senior-dev/senior-dev.md
│   ├── qa/qa.md
│   ├── researcher/researcher.md
│   ├── ux-designer/ux-designer.md
│   ├── devops/devops.md
│   ├── security-reviewer/security-reviewer.md
│   └── technical-writer/technical-writer.md
├── skills/
│   ├── split/SKILL.md           # Main orchestrator skill
│   └── retro/SKILL.md           # Retrospective skill
├── hooks/
│   └── hooks.json               # UserPromptSubmit orchestration hook
└── settings.json                 # Default plugin settings
```

### Installation

```
claude plugin add <git-repo-url>
```

User gets the full team, orchestrator, and retro engine immediately.

### Portability

The persona definitions are plain markdown with YAML frontmatter — trivially convertible to system prompts on any platform. The orchestration prompt is plain text. Only the hooks and agent-dispatch layer are Claude Code specific, forming a thin adapter that can be replicated for other systems.

## Open Questions for Future Iteration

- **Mediator agent for tiebreaking:** Could a third agent (pragmatic engineering manager) resolve Dev/QA disagreements before escalating to the user? The retro will surface whether this is needed based on escalation frequency.
- **Parallel ticket execution:** When tickets have no dependencies between them (e.g., UX Designer and Security Reviewer can work simultaneously), should the execution engine dispatch them in parallel?
- **Persona self-proposal:** Could personas propose updates to their own definitions during work (not just during retros)? "I keep needing to ask about encoding — I should add that to my checklist."
- **Cross-project learning:** Should persona memory be shareable across projects for universal lessons? Or is project-scoped memory always the right boundary?
