# Dashboard TUI Mockup

## Single-spec view (typical)

```
┌─ S001-rate-limiting ── Rate limiting to API endpoints ── complex ─────────────────────────────┐
│                                                                                                │
│  M001: Design & core implementation                                            [3/4 done]      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                          │
│  │  ○ BACKLOG   │ │  ● ACTIVE    │ │  ⏸ APPROVAL  │ │  ✓ DONE      │                          │
│  │              │ │              │ │              │ │              │                          │
│  │              │ │ T003a        │ │              │ │ T001         │                          │
│  │              │ │ senior-dev   │ │              │ │ tech-lead    │                          │
│  │              │ │ Fix race     │ │              │ │ Design       │                          │
│  │              │ │ condition    │ │              │ │ approach     │                          │
│  │              │ │              │ │              │ │ 18.2k tok    │                          │
│  │              │ │              │ │              │ │              │                          │
│  │              │ │              │ │              │ │ T002         │                          │
│  │              │ │              │ │              │ │ senior-dev   │                          │
│  │              │ │              │ │              │ │ Implement    │                          │
│  │              │ │              │ │              │ │ middleware   │                          │
│  │              │ │              │ │              │ │ 42.5k tok    │                          │
│  │              │ │              │ │              │ │              │                          │
│  │              │ │              │ │              │ │ T003         │                          │
│  │              │ │              │ │              │ │ qa           │                          │
│  │              │ │              │ │              │ │ Adversarial  │                          │
│  │              │ │              │ │              │ │ review       │                          │
│  │              │ │              │ │              │ │ 24.1k tok    │                          │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘                          │
│                                                                                                │
│  M002: Integration & hardening                                           [blocked ── 0/2]      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                          │
│  │  ○ BACKLOG   │ │  ● ACTIVE    │ │  ⏸ APPROVAL  │ │  ✓ DONE      │                          │
│  │              │ │              │ │              │ │              │                          │
│  │ T004         │ │              │ │              │ │              │                          │
│  │ senior-dev   │ │              │ │              │ │              │                          │
│  │ Headers &    │ │              │ │              │ │              │                          │
│  │ docs         │ │              │ │              │ │              │                          │
│  │              │ │              │ │              │ │              │                          │
│  │ T005         │ │              │ │              │ │              │                          │
│  │ qa           │ │              │ │              │ │              │                          │
│  │ End-to-end   │ │              │ │              │ │              │                          │
│  │ validation   │ │              │ │              │ │              │                          │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘                          │
│                                                                                                │
│ ── Activity ──────────────────────────────────────────────────────────────────────────────────  │
│  10:53  T003 qa         Blockers: 1 (race condition) → follow-up T003a                         │
│  10:52  T002 senior-dev Done  42.5k tokens  artifact: src/middleware/rate-limiter.ts            │
│  10:45  T002 senior-dev Question: "Redis or in-memory?" → user: "Redis"                        │
│  10:38  T001 tech-lead  Done  18.2k tokens  artifact: artifacts/T001-approach.md                │
│  10:32  T001 tech-lead  Dispatched                                                             │
│                                                                                                │
│ ── Metrics ───────────────────────────────────────────────────────────────────────────────────  │
│  Tickets: 3/5 done  │  Dispatches: 5  │  Follow-ups: 1  │  Questions: 2  │  Tokens: 84.8k     │
│  Milestones: 0/2    │  Elapsed: 35m   │  Last activity: 2m ago                                 │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Multi-spec view

When multiple specs are active, the header becomes a tab bar. Press `s` to cycle:

```
┌─ [S001-rate-limiting] ── S002-auth-refactor ──────────────────────────────────────────────────┐
│  ...active spec's board, activity, and metrics shown here...                                   │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Medium-complexity spec (no milestones)

Flat ticket list, no milestone headers:

```
┌─ S003-quick-bugfix ── Fix login redirect loop ── medium ──────────────────────────────────────┐
│                                                                                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                          │
│  │  ○ BACKLOG   │ │  ● ACTIVE    │ │  ⏸ APPROVAL  │ │  ✓ DONE      │                          │
│  │              │ │              │ │              │ │              │                          │
│  │ T002         │ │ T001         │ │              │ │              │                          │
│  │ qa           │ │ senior-dev   │ │              │ │              │                          │
│  │ Review fix   │ │ Fix redirect │ │              │ │              │                          │
│  │              │ │ logic        │ │              │ │              │                          │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘                          │
│                                                                                                │
│ ── Activity ──────────────────────────────────────────────────────────────────────────────────  │
│  14:20  T001 senior-dev Dispatched                                                             │
│                                                                                                │
│ ── Metrics ───────────────────────────────────────────────────────────────────────────────────  │
│  Tickets: 0/2 done  │  Dispatches: 1  │  Follow-ups: 0  │  Questions: 0  │  Tokens: 0         │
└────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Pending approval state

When a ticket hits `pending_approval`, it stands out in its own column:

```
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                          │
│  │  ○ BACKLOG   │ │  ● ACTIVE    │ │  ⏸ APPROVAL  │ │  ✓ DONE      │                          │
│  │              │ │              │ │              │ │              │                          │
│  │              │ │              │ │ T006         │ │ T001         │                          │
│  │              │ │              │ │ sec-reviewer │ │ tech-lead    │                          │
│  │              │ │              │ │ Threat model │ │ Design       │                          │
│  │              │ │              │ │ ⚠ NEEDS YOU  │ │ approach     │                          │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘                          │
```

## Keyboard shortcuts

```
  s     cycle active spec (multi-spec only)
  q     quit dashboard
```

## Color scheme (in actual curses rendering)

- Backlog tickets: dim/grey
- Active tickets: bright white
- Pending approval: yellow, pulsing "NEEDS YOU" label
- Done tickets: green
- Failed/skipped: red
- Activity timestamps: dim
- Activity personas: colored per-persona (consistent mapping)
- Metrics values: bold
