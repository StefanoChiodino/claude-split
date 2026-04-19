# Gastown (SGT) — Feature Analysis

## 1. Overview and Positioning

SGT (Simple GitHub Gastown) is an ops-first AI agent orchestration system that leverages GitHub's native infrastructure — Issues, PRs, and the `gh` CLI — as its source of truth. Rather than building custom distributed systems, it uses tmux workers, a thin Bash/Node abstraction layer, and GitHub's primitives for state management.

**Target audience:** Operators running autonomous AI agent fleets that need deterministic orchestration, durable idempotency, and transparent GitHub-tracked state — particularly for continuous/ongoing operations rather than one-shot projects.

**Maturity:** Active development (April 2026). Includes comprehensive test suites (proof paths), web UI, and a sophisticated multi-tier control plane (Mayor, President, Refinery, Witness).

**Repo:** github.com/codejeet/sgt

## 2. Workflow Orchestration Model

SGT implements a **deterministic, plan-driven orchestration model**:

**Core architecture:**
- **Source of truth:** GitHub Issues + PRs
- **Execution:** tmux-based worker sessions ("polecats")
- **Operations:** `gh` CLI + thin Bash/Node layer

**Plan system (SGT_PLAN.json):**
```json
{
  "version": 1, "rig": "name",
  "policy": {"max_in_flight": 2},
  "completion_condition": "real definition of done",
  "acceptance": {"status": "pending|verified|blocked|waived"},
  "tasks": [{"id": "task-id", "title": "...", "depends_on": [...]}]
}
```

Plans provide deterministic work scheduling without LLM planning. Acceptance status values enforce completion semantics — pending work cannot falsely report success; blocked conditions prevent idle-green.

**Parallel execution:** Controlled via `SGT_MAYOR_DISPATCH_MAX_PARALLEL` (default 3). Multiple workers can run simultaneously within configured budgets.

**Ralph Mode:** Pins rigs into ongoing work until explicit operator conditions are satisfied. Prevents false completion signaling when intermediate tasks merge but larger conditions remain unmet.

## 3. Agent/Persona Architecture

SGT uses a **hierarchical worker/supervisor model**:

- **Polecats** — tmux worker sessions executing individual task branches
- **Dogs** — specialized workers for specific integration patterns
- **Mayor** — orchestrator managing work queuing, dispatch decisions, cross-rig coordination
- **President** (optional) — cross-rig supervisor managing hierarchical control plane
- **Witness** — monitors open PRs and merge readiness
- **Refinery** — handles merge queue management and CI check validation
- **Deacon** — background service with heartbeat monitoring

**Shared rig memory (SGT_CONTEXT.md):**
- Durable per-rig shared state persisting across worker sessions
- Agents read context before work; append findings on exit
- Optional semantic search via OpenAI embeddings

**Custom agents:** SGT is agent-agnostic — workers are tmux sessions that can run any CLI agent. The system orchestrates via GitHub state, not agent-specific APIs.

## 4. UX and Developer Experience

**Interface:** CLI (`sgt` command) + Web UI (localhost:4747)

**Key commands:**
- `sgt status` — human-readable overview with health indicators
- `sgt status --json` — machine-readable state
- `sgt trail` — recent activity with signal/noise classification
- `sgt peek mayor` — inspect Mayor's transient context
- `sgt create plan <rig> "<prompt>"` — create deterministic work plans
- `sgt create blocker <rig> "evidence"` — mark acceptance blockers
- `sgt config ralph <rig> --enable` — configure ongoing operation mode

**Web cockpit:** Real-time monitoring, dispatch controls, President/Mayor visibility, alert rail.

**Configuration:** Heavy use of environment variables (30+) for fine-grained control over timeouts, retry behavior, parallelism, and alert thresholds.

## 5. Extensibility and Customization

**Configuration granularity:** 30+ environment variables controlling every aspect of orchestration behavior:
- Dispatch parallelism, cooldowns, dedup windows
- Watchdog thresholds for CI, heartbeats, stale reviews
- Retry counts, backoff parameters, jitter
- Architecture mode (shared Mayor vs. per-rig with President)

**Rig system:** Named rigs map to GitHub repos, each configurable independently.

**Notification contract:** Configurable via `~/.sgt/.sgt/notify.json` for alert delivery.

**Plan requests:** Natural-language specs convertible to deterministic work plans.

**No plugin system:** Extensibility is through configuration, rig mapping, and worker customization rather than a plugin marketplace.

## 6. Reliability and Error Handling

SGT has the **most sophisticated reliability engineering** of the tools analyzed:

**Idempotency fences (pervasive):**
- Dispatch dedup via `repo+PR+merged_head_SHA` keying
- Cooldown suppression for duplicate wake events
- Per-attempt records with bounded retry on timeout
- Action receipts with expected/observed state verification

**Merge safety:**
- Pre-merge live state revalidation
- Review approval capture with `REVIEWED_HEAD_SHA` persistence
- Merge idempotency keying
- Post-merge verification with receipt durability
- Auto-merge fallback for branch policy failures
- Head drift revalidation before each retry

**Watchdog monitoring:**
- CI self-healing (auto-dispatch fix issues for red master)
- Refinery stall detection and escalation
- Agent heartbeat monitoring
- CI check timeout detection
- Deacon supervision with auto-restart
- Stranded rig detection with replacement dispatch

**Context window management:**
- Prompt size estimated as `ceil(char_count / 4)` tokens
- Auto-refresh at configurable threshold (default 150k tokens)
- Cooldown prevents thrashing (default 900s)
- Archives transient context, schedules clean restart

**Stale event guards:** Live revalidation immediately pre-spawn prevents acting on stale state.

**Sweep exit codes:** Deterministic failure semantics with actionable stderr.

## 7. Git Integration and Code Isolation

Git (via GitHub) is the **primary state management layer**:

**Work isolation:**
- Each worker (polecat) operates on an individual task branch
- Workers are tmux sessions with independent working directories
- Worktrees used for isolation (cleanup on stale polecat reconciliation)

**Merge workflow (Refinery):**
1. PR created from worker branch
2. Witness monitors merge readiness
3. Refinery validates, reviews, and manages merge queue
4. Pre-merge validation, merge attempt with retry, post-merge verification
5. Conflict detection with re-sling dedup

**GitHub-native state:**
- Issue lifecycle tracked via labels (`sgt-authorized`, state transitions)
- PR states (OPEN/MERGED) with post-merge verification fences
- Plan-aware completion conditions prevent false DONE signaling

**Security gate:** `sgt-authorized` label required before dispatch (configurable via `SGT_REQUIRE_AUTH_LABEL`).

## 8. Strengths and Weaknesses Summary

**Strengths:**
- Extremely robust reliability engineering (idempotency fences, dedup, retry with verification)
- GitHub-native — transparent state, familiar primitives, full audit trail
- Deterministic planning (no LLM-generated plans — human-authored or templated)
- Self-healing (CI auto-fix, heartbeat monitoring, stale worker cleanup)
- Ralph Mode for ongoing operations (not just one-shot projects)
- Hierarchical control plane (Mayor → President) scales across rigs
- Web cockpit for real-time visibility
- Context window auto-refresh prevents OOM
- Agent-agnostic workers

**Weaknesses:**
- High operational complexity — 30+ env vars, multiple daemon processes
- No built-in code quality enforcement (TDD, review gates)
- GitHub-coupled — cannot operate without GitHub Issues/PRs
- No spec-first workflow or design discovery phase
- No persona-based decomposition — workers are generic
- CLI-heavy UX may overwhelm new users
- No multi-model optimization
- Single-developer setup overhead is substantial
- Documentation is reference-heavy, lacks tutorials
