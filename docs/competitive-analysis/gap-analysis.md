# Gap Analysis — claude-split vs. Competitors

## Feature Comparison Matrix

| Capability | claude-split | Factory Missions | Superpowers | Paperclip AI | Gastown (SGT) |
|---|---|---|---|---|---|
| **Workflow Orchestration** | | | | | |
| Multi-step task decomposition | Full | Full | Full | Partial (company-level) | Full |
| Dependency management | Full | Partial (milestones only) | Absent | Absent | Full |
| Parallel execution | Full (worktree isolation) | Partial (targeted) | Absent | Full (heartbeat-based) | Full (configurable) |
| Session persistence | Full (board.yaml) | Full (git + orchestrator) | Partial (plan files only) | Full (PostgreSQL) | Full (GitHub + filesystem) |
| Multi-day autonomous work | Absent | Full (up to 16 days) | Absent | Full | Full |
| **Agent/Persona Architecture** | | | | | |
| Named personas/roles | Full (11 personas) | Partial (3 roles) | Partial (1 agent + subagent prompts) | Partial (org chart roles) | Partial (Mayor/Polecat/Refinery) |
| Custom persona definition | Full | Partial (custom Droids) | Absent | Full (hire any agent) | Partial (worker config) |
| Multi-model per role | Absent | Full | Absent | Absent | Absent |
| Persona communication protocol | Full (artifacts + board) | Full (git handoffs) | Partial (subagent prompts) | Full (task + hierarchy) | Full (GitHub Issues/PRs) |
| **UX/Developer Experience** | | | | | |
| Zero-config start | Partial (/split command) | Partial (/enter-mission) | Full (auto-triggers) | Absent (setup required) | Absent (heavy config) |
| Spec-first workflow | Full | Full | Full | Absent | Absent |
| Progress dashboard | Full (TUI + board) | Full (Mission Control) | Absent | Full (React UI) | Full (Web cockpit) |
| Mid-execution intervention | Partial (decisions) | Full (PM-style control) | Partial (gate approvals) | Full (management overrides) | Full (Mayor direction) |
| **Extensibility** | | | | | |
| Plugin/skill system | Absent (monolithic) | Absent | Full (14 composable skills) | Full (plugin ecosystem) | Absent |
| Hooks/lifecycle events | Full (Claude Code hooks) | Full (lifecycle hooks) | Partial (platform hooks) | Full (governance gates) | Full (env-based config) |
| Cross-platform support | Absent (Claude Code only) | Absent (Factory only) | Full (6 platforms) | Full (any agent) | Full (any tmux agent) |
| MCP integration | Absent | Full | Absent | Full (MCP server) | Absent |
| **Reliability** | | | | | |
| Idempotency fences | Absent | Partial (validation gates) | Absent | Partial (atomic checkout) | Full (pervasive) |
| Self-healing / watchdog | Absent | Partial (re-planning) | Absent | Absent | Full |
| Context window management | Absent | Full (fresh sessions) | Full (fresh subagents) | N/A (external agents) | Full (auto-refresh) |
| Budget/cost control | Absent | Absent | Absent | Full | Absent |
| Review/verification gates | Full (code reviewer + verifier) | Full (validation workers) | Full (two-stage review) | Full (board approval) | Partial (refinery review) |
| **Git Integration** | | | | | |
| Worktree isolation | Full (per-ticket) | Partial (per-feature) | Full (per-project) | Absent | Full (per-worker) |
| Automated merge management | Partial (orchestrator merges) | Partial (milestone validation) | Full (branch finishing skill) | Absent | Full (Refinery) |
| Conflict resolution | Partial (dispatch to agent) | Partial (re-planning) | Absent | Absent | Full (re-sling with dedup) |
| PR/merge queue | Absent | Absent | Absent | Absent | Full |

## Identified Gaps

### Gap 1: Multi-Day Autonomous Execution

**What claude-split lacks:** The ability to run autonomously across sessions/days without user interaction.

**Demonstrated by:** Factory Missions (up to 16 days), Gastown (ongoing Ralph Mode), Paperclip (continuous heartbeat)

**Implementation:** Factory uses persistent orchestrator state + fresh worker sessions; Gastown uses filesystem state + GitHub-tracked progress; Paperclip uses PostgreSQL persistence.

### Gap 2: Multi-Model Optimization

**What claude-split lacks:** Assigning different LLM models to different persona roles based on cost/capability tradeoffs.

**Demonstrated by:** Factory Missions (Opus for orchestration, Sonnet for implementation, GPT-5.3 for validation, Kimi for research)

**Implementation:** Factory's orchestrator selects the model per worker role at dispatch time.

### Gap 3: Context Window Management

**What claude-split lacks:** Active strategies to prevent context degradation in long-running operations.

**Demonstrated by:** Superpowers (fresh subagent per task), Factory (fresh sessions per feature), Gastown (auto-refresh at token threshold)

**Implementation:** Superpowers dispatches a clean subagent per task; Factory starts fresh sessions per feature; Gastown estimates token usage and triggers refresh/restart when threshold is hit.

### Gap 4: Idempotency and Durability

**What claude-split lacks:** Fences preventing duplicate operations, durable receipts for completed actions, and safe restart behavior.

**Demonstrated by:** Gastown (pervasive idempotency keying, action receipts, dispatch dedup, merge receipts)

**Implementation:** Gastown keys operations by `repo+PR+SHA`, stores attempt/receipt records on filesystem, and revalidates live state before every action.

### Gap 5: Self-Healing and Watchdog Monitoring

**What claude-split lacks:** Automatic detection and recovery of stalled agents, failed CI, or stuck operations.

**Demonstrated by:** Gastown (CI self-healing, heartbeat monitoring, stale worker cleanup, refinery stall detection)

**Implementation:** Gastown runs watchdog loops checking heartbeat freshness, CI status, review progress; auto-dispatches fix issues or restarts stalled components.

### Gap 6: Cross-Platform Support

**What claude-split lacks:** Running on platforms other than Claude Code.

**Demonstrated by:** Superpowers (Claude Code, Cursor, Codex, OpenCode, Copilot CLI, Gemini CLI)

**Implementation:** Superpowers provides platform-specific install docs and adapts to each platform's plugin/extension mechanism.

### Gap 7: Composable Skill System

**What claude-split lacks:** A modular, user-extensible skill library where individual workflows can be added/modified independently.

**Demonstrated by:** Superpowers (14 composable skills, `writing-skills` meta-skill for creating new ones)

**Implementation:** Each skill is a self-contained SKILL.md file with trigger conditions and process definitions. Users create new skills following the template.

### Gap 8: Budget and Cost Control

**What claude-split lacks:** Tracking and limiting token/cost spend per agent or ticket.

**Demonstrated by:** Paperclip (per-agent monthly budgets, automatic throttling, runaway spend prevention)

**Implementation:** Paperclip enforces budget ceilings per agent, throttles when approaching limits, and provides cost dashboards.

### Gap 9: Merge Queue and PR Workflow

**What claude-split lacks:** Automated PR review, merge queuing, and CI validation before merge.

**Demonstrated by:** Gastown (Refinery with merge queue, review loops, CI check validation, conflict handling)

**Implementation:** Gastown's Refinery queues PRs, validates merge readiness, handles conflicts with re-sling, and provides exponential backoff retry.

### Gap 10: Mid-Execution Scope Changes

**What claude-split lacks:** Rich intervention model for redirecting work during execution beyond simple decisions.

**Demonstrated by:** Factory Missions (drop/add features, redirect priorities, re-plan milestones), Gastown (Ralph Mode conditions, dynamic plan modification)

**Implementation:** Factory allows PM-style direction changes; Gastown's Ralph Mode pins ongoing conditions; both allow live re-scoping without abandoning progress.

## High-Value Gaps

### 1. Context Window Management (Small complexity)

**Why high-value:** Long-running specs with many tickets will degrade quality as the orchestrator's context fills. This directly impacts reliability of the core workflow.

**Recommendation:** Dispatch each ticket's persona-agent with `isolation: "worktree"` (already done) which gives fresh context. For the orchestrator itself, implement a compaction strategy: after each ticket completion, summarize the execution so far and trim older detailed context. Track estimated token usage and warn when approaching limits.

**Estimated complexity:** Small — fresh agents per ticket already exists. Add orchestrator compaction heuristic.

### 2. Idempotency and Safe Restart (Medium complexity)

**Why high-value:** If a session crashes mid-execution, resuming should not re-dispatch already-completed work or duplicate merges. Currently, resumption reads board state but has no fence against duplicate operations.

**Recommendation:** Add a dispatch log keyed by `ticket_id + branch_SHA`. Before dispatching, check if an active worktree branch already exists for that ticket. Before merging, check if the ticket branch is already merged. Store lightweight receipts in `board.yaml` (merge SHA per ticket). The existing `status` field partially covers this but lacks SHA-level verification.

**Estimated complexity:** Medium — requires dispatch dedup keying and merge verification.

### 3. Multi-Model per Persona (Small complexity)

**Why high-value:** Using Opus for orchestration/review and Sonnet/Haiku for implementation could reduce costs 3-5x on large specs without quality loss on routine implementation tasks.

**Recommendation:** Add a `model` field to ticket definitions or persona defaults. The `Agent` tool already accepts a `model` parameter — thread the persona's configured model through to the dispatch call. Default: orchestrator=opus, senior-dev=sonnet, test-writer=sonnet, verifier=opus.

**Estimated complexity:** Small — infrastructure already supports it via Agent tool's `model` parameter.

### 4. Self-Healing Agent Monitoring (Large complexity)

**Why high-value:** Agents that stall silently (context limit hit, tool error, infinite loop) waste time. Detection + auto-retry would make unattended operation reliable.

**Recommendation:** Track dispatch time per ticket. If an agent hasn't returned within a configurable timeout, mark the ticket as failed and trigger the error escalation ladder. For background agents, monitor the output file for completion. Add a `--timeout` option to ticket definitions.

**Estimated complexity:** Large — requires background monitoring loop, timeout tracking, and integration with the error handling system.

## Lower-Priority Gaps

| Gap | Rationale for deprioritization |
|---|---|
| Multi-day autonomous execution | claude-split operates within a single Claude Code session by design; multi-day would require a fundamentally different architecture |
| Cross-platform support | Claude Code plugin system is the primary delivery mechanism; other platforms have different plugin architectures |
| Budget/cost control | Token tracking exists (metrics.yaml) but enforcement would add complexity for limited benefit at current scale |
| Merge queue/PR workflow | claude-split's merge-back-to-split-branch model is simpler than Gastown's but sufficient for its use case |
| Composable skill system | Split's value is in the full orchestrated workflow, not individual skills; decomposing it would lose the coordinated benefit |
| Mid-execution scope changes | The spec amendment flow already exists; richer intervention adds complexity for an edge case |
