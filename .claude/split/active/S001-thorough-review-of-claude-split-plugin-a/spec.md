# Spec: Thorough Review of the claude-split Plugin

## Objective

Conduct a comprehensive review of the claude-split plugin across all dimensions: plugin structure and best practices compliance, code quality of the board CLI, SKILL.md orchestrator design, persona definitions, hook implementation, test coverage, and overall architecture. The review should produce concrete, actionable findings organized by severity, along with a prioritized list of recommended improvements.

## Scope

### In scope

1. **Claude Code plugin best practices compliance** -- Does the plugin follow the conventions observed in the Claude Code plugin ecosystem? Covers plugin.json schema, directory layout, marketplace.json, skill definition, agent definition, hooks, and tool distribution.

2. **SKILL.md (orchestrator) review** -- Is the orchestrator prompt well-structured, unambiguous, and likely to produce reliable behavior from the LLM? Are there gaps, contradictions, or instructions that would confuse the model?

3. **Persona review (all 11 personas + shared core-operating-principle)** -- For each persona: clarity of role boundaries, tool access appropriateness, model/effort level selection, risk of overlap with other personas, quality of behavioral instructions, and whether the persona would actually produce useful output when dispatched.

4. **Board CLI code quality** -- Review of the Python CLI (`split_board/`) for correctness, error handling, edge cases, maintainability, and architectural concerns.

5. **Hook implementation** -- Review of `install-cli.sh` and `guard-board.sh` for correctness, security, robustness, and cross-platform concerns.

6. **Test coverage** -- Gaps in the test suite, untested edge cases, test quality.

7. **Dashboard** -- Review of the Textual TUI dashboard for correctness and usability.

8. **Documentation** -- README accuracy, install instructions, user-facing discoverability.

### Out of scope

- Performance benchmarking of the CLI
- End-to-end testing of the plugin within a live Claude Code session (manual QA)
- Rewriting or implementing fixes (this spec covers the review only; fixes become separate tickets)
- Review of the design docs in `docs/superpowers/` (these are historical design artifacts, not active code)

## Deliverables

A single comprehensive review report written to `docs/review-2026-04-14.md`, organized into the following sections, each containing findings with severity levels:

### 1. Plugin Structure and Best Practices

Review against Claude Code plugin conventions:

- **Directory layout**: Does the plugin follow the expected `<plugin-root>/.claude-plugin/plugin.json`, `agents/`, `skills/`, `hooks/`, `tools/` structure? Are there any unexpected files or missing expected files?
- **plugin.json**: Does it contain all expected fields? Are `license` and `keywords` standard or non-standard? Is `version` semantic?
- **marketplace.json**: Is the marketplace entry correctly structured? Does `source` point to the right path? Does the `plugins` array schema match what the marketplace expects?
- **Skill definition**: Does `SKILL.md` frontmatter use correct fields (`name`, `description`)? Is the description field useful for Claude's auto-invocation heuristic?
- **Agent definitions**: Do all agents follow the same frontmatter schema? Are the frontmatter fields (`name`, `description`, `model`, `effort`, `tools`) correct and consistent? Is the `@agents/shared/` import syntax valid?
- **Hooks**: Does `hooks.json` use the correct schema? Are the hook types (`SessionStart`, `PreToolUse`) and matchers correct? Is `CLAUDE_PLUGIN_ROOT` and `CLAUDE_ENV_FILE` used correctly?
- **Tool distribution**: Is the Python package correctly structured for installation via the `install-cli.sh` hook? Is `pyproject.toml` correctly configured?

### 2. Orchestrator (SKILL.md) Review

- **Phase coverage**: Are all phases (worktree, spec, execution, demo, git decision, archive) well-defined? Are there gaps between phases?
- **Instruction clarity**: Could the LLM misinterpret any instructions? Are there ambiguous directives?
- **Role boundary enforcement**: The orchestrator is told it can only run `split-board`, `git`, and read tools. Is this boundary clear enough? Are there scenarios where the orchestrator would be forced to break it?
- **Error handling**: Are error recovery paths complete? What happens on partial failures?
- **Session resumption**: Is the resumption flow robust? What state could be lost between sessions?
- **Complexity classification**: Is "Medium vs. Complex" clear enough, or will it produce inconsistent categorization?
- **Missing instructions**: Are there workflow states not covered (e.g., what if the user interrupts mid-execution)?

### 3. Persona Review (all 11 + shared)

For each persona, evaluate:

- **Role clarity**: Is the persona's job unambiguous? Would the LLM know what to do when dispatched?
- **Boundary definition**: Where does this persona's responsibility end and another's begin? Are there overlaps that would cause confusion?
- **Tool access**: Are the tools appropriate for the role? Any missing tools that would prevent the persona from doing its job? Any unnecessary tools that could cause harm?
- **Model and effort level**: Is the model/effort appropriate for the complexity of the persona's typical tasks?
- **Behavioral instructions**: Are the "How You Work" sections specific enough to guide behavior, or are they vague platitudes?
- **Output format**: Does the persona define what its output should look like? Would the orchestrator know what to do with the output?
- **Core operating principle inclusion**: Does every persona correctly reference the shared file?
- **Cross-persona interactions**: When the SKILL.md says persona A hands off to persona B, do both personas' definitions support that handoff?

Specific concerns to investigate per persona:

| Persona | Key questions |
|---------|--------------|
| SME | Does it have Edit tool? Should it? Can it actually write specs without Write tool confusion? |
| Tech Lead | Has Agent tool -- when would it use it? Is that appropriate? |
| Senior Dev | Effort is `medium` while most others are `high` -- is implementation really less complex than review? |
| Test Writer | Can it run tests (Bash access) to verify its tests are valid? |
| Code Reviewer | Read-only tools (no Edit/Write) -- correct for the role? Can it still create follow-up tickets? |
| Verifier | Read-only tools -- can it run tests via Bash? Should it be able to? |
| UX Designer | Has Write tool -- appropriate? What would it write? |
| DevOps | Has Edit/Write -- appropriate for infra changes? Security concern? |
| Researcher | Has WebSearch and WebFetch -- are these real Claude Code tools? |
| Technical Writer | Effort is `low` -- is documentation really that simple? |
| Security Reviewer | Read-only -- correct? Should it be able to write threat model documents? |

### 4. Board CLI Code Quality

- **Correctness**: Are there logical bugs in state transitions, dependency management, cycle detection, or status recomputation?
- **Error handling**: Does `error()` call `sys.exit(1)` -- is that appropriate for a library that's also tested via `main()`? Does it make testing harder?
- **Edge cases**: What happens with empty boards, no milestones, duplicate IDs, concurrent access?
- **Dashboard path resolution**: `cmd_dashboard` computes the dashboard script path as `Path(__file__).parent.parent.parent / "split" / "tools" / "split_board_dashboard.py"` -- this path is almost certainly wrong for the installed plugin context. Is this a known bug?
- **YAML safety**: Is `yaml.safe_load` sufficient? Are there risks of YAML-specific issues?
- **Validation completeness**: Does `validate_board()` catch all invalid states?
- **Metrics accuracy**: Are the computed metrics correct for all board states?

### 5. Hook Review

- **install-cli.sh**: Is the auto-permission injection (`settings.local.json` modification) safe? What if `jq` is not installed? What about race conditions with concurrent sessions? Is `uv pip install -e` the right choice for a plugin (editable install vs. regular install)?
- **guard-board.sh**: Does the `case` pattern reliably match all board.yaml paths? Could it be bypassed? Does it handle JSON input correctly?
- **Cross-platform**: Do these hooks work on Linux? Windows (WSL)? Are there shell portability issues?

### 6. Test Coverage Analysis

- **Coverage gaps**: What CLI commands or code paths lack test coverage?
- **Dashboard testing**: The dashboard has zero test coverage -- is that acceptable?
- **Validation edge cases**: Are all validation rules tested?
- **Error path testing**: Are error messages and exit codes tested?
- **Integration concerns**: Tests use `main()` directly, which calls `sys.exit()` -- is `pytest.raises(SystemExit)` the right pattern here?

### 7. Documentation Review

- **README**: Are the install instructions correct? Is the `/plugin marketplace add` syntax accurate?
- **Discoverability**: Would a new user understand how to use the plugin from the README alone?
- **Missing docs**: Is there any missing documentation for the board CLI, personas, or workflow?

## Finding Severity Levels

Each finding should be categorized as:

- **Critical** -- Broken functionality, security issue, or something that prevents the plugin from working
- **High** -- Significant issue that degrades the user experience or causes incorrect behavior in common cases
- **Medium** -- Issue that affects edge cases or is a maintainability concern
- **Low** -- Style, documentation, or minor improvement suggestion

## Acceptance Criteria

1. Every file in the plugin has been read and considered (not just skimmed)
2. Each of the 7 review sections contains specific findings with severity, evidence (file paths and line numbers), and a concrete recommendation
3. The persona review covers all 11 personas individually, not just a summary
4. At least the dashboard path bug in `commands.py:465` is called out as a concrete example of a real bug
5. The review distinguishes between "this is broken" and "this could be better" -- not everything should be a blocker
6. Findings are prioritized so the reader knows what to fix first
