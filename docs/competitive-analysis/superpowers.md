# Superpowers Plugin — Feature Analysis

## 1. Overview and Positioning

Superpowers is an open-source (MIT) Claude Code plugin that provides a complete software development workflow through composable "skills." Created by Jesse Vincent (Prime Radiant), it enforces disciplined development practices — TDD, spec-first design, implementation planning — via automatically-triggered skill modules.

**Target audience:** Individual developers and small teams using Claude Code who want structured, quality-enforcing workflows without manual discipline. Also supports Cursor, Codex, OpenCode, GitHub Copilot CLI, and Gemini CLI.

**Maturity:** v5.0.7 (April 2026), available in the official Claude plugin marketplace. Active community on Discord, MIT licensed, with a fork ecosystem (0x-chad/superpowers, hgahlot/claude-flow, etc.).

## 2. Workflow Orchestration Model

Superpowers enforces a **sequential, gate-based workflow**:

1. **Brainstorming** — Socratic design refinement before any code is written
2. **Git worktree creation** — Isolated workspace on a new branch
3. **Plan writing** — Detailed implementation plan with bite-sized tasks (2-5 minutes each)
4. **Subagent-driven development** — Fresh subagent per task with two-stage review
5. **Code review** — Between tasks, against the plan
6. **Branch finishing** — Verify tests, present options (merge/PR/keep/discard)

**Execution model:** Serial task execution. Each task gets a fresh subagent to prevent context pollution. The orchestrating session coordinates and reviews, while subagents implement.

**State management:** Plans are saved to `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`. Progress tracked via TodoWrite (Claude Code's built-in task tracker). No persistent board or database.

**Session persistence:** Plans survive as files. TodoWrite items persist within the session. No cross-session state beyond the plan document itself.

## 3. Agent/Persona Architecture

Superpowers uses a **thin agent model** with one defined agent:

- **code-reviewer** agent (single agent definition in `agents/code-reviewer.md`)

The skill system creates implicit roles through subagent prompts:
- **Implementer subagent** — Fresh context, implements one task, self-reviews
- **Spec reviewer subagent** — Checks code matches spec
- **Code quality reviewer subagent** — Reviews for code quality

Agents are dispatched per-task (not parallel across tasks). The main session acts as the orchestrator, choosing which skill to invoke.

**Custom personas:** Not directly supported. Users can fork and modify the plugin or add their own skills, but there's no "add a persona" mechanism.

## 4. UX and Developer Experience

**Interface:** CLI-native via Claude Code slash commands and automatic skill triggering.

**Configuration:** Zero config — skills trigger automatically based on context. "Because the skills trigger automatically, you don't need to do anything special. Your coding agent just has Superpowers."

**Interaction pattern:**
- User starts working → brainstorming skill triggers automatically
- Agent presents design "in chunks short enough to actually read and digest"
- User signs off → plan is written with exact file paths, complete code, verification steps
- User says "go" → subagent-driven development executes autonomously

**Feedback loop:** Two-stage review after each task (spec compliance then code quality) provides continuous quality assurance without requiring user intervention between tasks. "It's not uncommon for Claude to be able to work autonomously for a couple hours at a time without deviating from the plan."

## 5. Extensibility and Customization

**Skill system:** 14 composable skills covering the full development lifecycle. Each skill is a Markdown file (SKILL.md) with trigger conditions and process definitions.

**Creating new skills:** The `writing-skills` skill guides users through creating custom skills following the plugin's conventions.

**Plugin marketplace:** Available on Claude Code official marketplace, Cursor, Codex, OpenCode, Copilot CLI, and Gemini CLI — broad platform reach.

**Hooks:** The plugin uses Claude Code's hook system but no custom hooks beyond platform defaults.

**Customization limitations:** Skills operate as autonomous workflows — users influence them by approving/rejecting at gate points but can't easily modify skill behavior mid-execution.

## 6. Reliability and Error Handling

**Context isolation:** Fresh subagent per task prevents context pollution and attention degradation. The main orchestrator preserves its context for coordination only.

**Review gates:** Two-stage review (spec compliance + code quality) catches issues per task rather than at the end.

**TDD enforcement:** RED-GREEN-REFACTOR cycle ensures tests exist before implementation. "Deletes code written before tests."

**Verification before completion:** Dedicated skill (`verification-before-completion`) ensures claims of success are backed by evidence — "requires running verification commands and confirming output before making any success claims."

**Error recovery:** If a subagent fails or produces poor work, the review stage catches it and the implementer subagent is re-dispatched to fix. Loop continues until review passes.

**Context window limits:** Fresh subagent per task means each task operates within a clean context window. The orchestrator session may still hit limits on very large projects.

## 7. Git Integration and Code Isolation

**Git worktrees:** The `using-git-worktrees` skill creates isolated workspaces on new branches before implementation begins.

**Workflow:**
1. Create worktree with new branch
2. Run project setup, verify clean test baseline
3. Implement tasks (each task committed separately)
4. Finish branch: verify tests, present options (merge, PR, keep, discard)

**Commit discipline:** Plans specify "frequent commits" and TDD enforces commit after each RED-GREEN cycle.

**Branch finishing:** The `finishing-a-development-branch` skill handles merge decisions, cleanup, and worktree removal.

## 8. Strengths and Weaknesses Summary

**Strengths:**
- Zero configuration — skills trigger automatically
- Strong quality enforcement (TDD, two-stage review, verification)
- Cross-platform (Claude Code, Cursor, Codex, OpenCode, Copilot CLI, Gemini CLI)
- Open source (MIT), active community
- Fresh subagent per task prevents context degradation
- Bite-sized tasks (2-5 min each) make progress visible and reviewable
- Plan documents provide clear project record

**Weaknesses:**
- Single orchestrator session — no true parallelization across tasks
- Only one agent definition (code-reviewer) — no rich persona system
- No persistent board/state across sessions (relies on plan files + TodoWrite)
- No kanban/progress tracking beyond TodoWrite items in-session
- No milestone concept or dependency management
- Cannot handle multi-day autonomous work — bound to single session
- No multi-model optimization (uses whatever model the session runs on)
- Limited intervention model — user approves/rejects at gates but can't redirect mid-task
