# Factory Droid — Missions Feature Analysis

## 1. Overview and Positioning

Factory (factory.ai) is an enterprise AI coding platform. Missions is their autonomous multi-day project execution feature, enabling users to describe complex objectives and have Factory's "Droid" agent handle decomposition, execution, and validation until completion.

**Target audience:** Enterprise engineering teams on Max/Enterprise plans needing autonomous execution of large-scale tasks (legacy migrations, greenfield apps, API documentation, test coverage generation, refactoring).

**Maturity:** Production (rolling out to Enterprise/Max subscribers), with some features still in "research preview" status. Median mission duration is 2 hours; longest observed is 16 days of continuous autonomous work.

## 2. Workflow Orchestration Model

Missions implements a **three-tier orchestration model**:

- **Orchestrator:** Breaks projects into milestones (meaningful checkpoints), manages coordination between workers
- **Workers:** Fresh sessions per feature with clean context to prevent attention degradation
- **Validators:** Test functionality, check regressions, verify integration at milestone boundaries

**Execution strategy:** Serial execution with targeted parallelization. Factory explicitly found that "serial execution with targeted parallelization has worked better than broad parallelism" to prevent coordination conflicts.

**Cost estimation formula:** `total runs ≈ #features + 2 * #milestones`

**Session persistence:** Workers operate in fresh sessions per feature. State is maintained through git (the "source of truth") and the orchestrator layer. Configuration, MCP integrations, custom skills, and AGENTS.md conventions carry forward across all workers.

**Multi-model architecture** assigns different models to different roles:
- Orchestration: Claude Opus 4.6
- Feature implementation: Sonnet 4.6 / Opus 4.6
- Validation: GPT-5.3-Codex
- Research: Kimi K2.5

## 3. Agent/Persona Architecture

Factory uses role-based agents rather than named personas:

- **Feature workers** — Execute individual features with specialized skills
- **Validation workers** — Verify milestone completion, run tests, check regressions; includes "native computer use" (launching apps, navigating flows, checking visual rendering)
- **Orchestrator agent** — Manages execution state; can be directed by users in real-time
- **Subagents** — Custom Droids configured in the project are available to workers

Users cannot add arbitrary custom personas but can configure custom Droids and skills. The skill system learns domain-specific patterns as Missions operate.

## 4. UX and Developer Experience

**Initiation:** Users run `/enter-mission` (or `/missions`) to begin a conversational planning phase. Droid asks clarifying questions and scopes the project collaboratively.

**Execution:** Users transition to "Mission Control" where they operate as project managers — monitoring progress, unblocking workers, and redirecting priorities. Users can:
- Pause the orchestrator and request re-assessment
- Mark items complete or redirect to next feature
- Drop features, add requirements, adjust scope mid-mission
- Unblock frozen/stuck workers

**Feedback loop:** "The biggest value we have found in Missions is in the planning phase." The system emphasizes upfront scoping with clear milestones before execution begins.

## 5. Extensibility and Customization

- **MCP integrations** carry forward (Linear, Sentry, Notion, etc.)
- **Custom skill library** — learns domain-specific patterns during Missions operation
- **Custom Droids** — user-configured subagents available to workers
- **Lifecycle hooks** — user hooks integrate custom security at key execution points
- **AGENTS.md conventions** — coding standards inherited by all workers

No public plugin marketplace — extensibility is through Factory's own configuration system.

## 6. Reliability and Error Handling

**Active intervention model:** Users function as PMs with the ability to intervene:
- Frozen missions can be paused, re-assessed
- Stuck workers can be redirected
- Blocked milestones trigger orchestrator re-planning

**Validation gates:** Every milestone ends with a validation phase: workers review accumulated work, run tests, check for regressions.

**Context management:** Fresh sessions per feature prevent attention degradation across long tasks. Token consumption is 12x higher than interactive sessions due to sustained execution, not intensity.

**Enterprise controls:**
- Risk-level classification for all commands
- Secret scanning via "Droid Shield" before model transmission
- Full action logging and OpenTelemetry telemetry

**Open questions (acknowledged by Factory):** Parallelization optimization, long-horizon correctness accumulation, ideal worker scope, and sub-orchestrator benefits remain active research areas.

## 7. Git Integration and Code Isolation

Git is explicitly "the source of truth" for all project work:
- Enables structured handoffs between worker sessions
- Maintains complete project history
- Workers operate on isolated features

Specific branching strategy details are not publicly documented beyond "workers branch per feature." Validation workers operate at milestone boundaries before merge.

## 8. Strengths and Weaknesses Summary

**Strengths:**
- Multi-day autonomous execution (up to 16 days observed)
- Multi-model architecture optimizes cost/capability per role
- Validation workers with native computer use (visual testing)
- Enterprise-grade security (SOC 2 Type II, ISO 27001, airgapped deployment)
- Active PM-style intervention model prevents runaway execution
- Emphasis on planning phase quality
- Configuration inheritance (MCP, skills, hooks) across all workers

**Weaknesses:**
- Enterprise-only pricing (Max/Enterprise plans)
- Closed ecosystem — no public plugin marketplace
- Limited parallelization by design (may be slower for embarrassingly parallel tasks)
- Research preview status for some features
- Git isolation details not publicly documented
- No community-driven extension model
