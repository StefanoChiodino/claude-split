# Spec S003: Competitive Analysis — Missions, Superpowers, Paperclip AI, Gastown

## Goal

Produce a structured competitive analysis of four AI coding workflow tools against claude-split. The analysis will inform the roadmap by identifying gaps in claude-split capabilities and surfacing design ideas worth adopting. Each tool gets its own standalone report; a fifth document synthesizes findings into a gap analysis with prioritized recommendations.

## Scope

### In scope

- Feature analysis of: Factory Droid Missions, Superpowers plugin, Paperclip AI, Gastown
- Comparison across 6 dimensions: workflow orchestration, agent/persona architecture, UX/DX, extensibility, reliability/error handling, git integration/code isolation
- Gap analysis identifying what claude-split is missing relative to these tools
- Concrete recommendations for high-value gaps

### Out of scope

- Implementation of any recommendations (those become separate specs)
- Analysis of tools beyond the four listed
- Pricing, licensing, or business model analysis (unless relevant to DX)
- Benchmarks or quantitative performance comparisons

## Deliverables

5 documents in docs/competitive-analysis/:

| # | File | Content |
|---|------|---------|
| 1 | factory-droid-missions.md | Feature analysis of Factory Droid Missions system |
| 2 | superpowers.md | Feature analysis of the Superpowers Claude Code plugin |
| 3 | paperclip-ai.md | Feature analysis of Paperclip AI |
| 4 | gastown.md | Feature analysis of Gastown |
| 5 | gap-analysis.md | Comparative gap analysis with recommendations |

## Requirements

### Report Structure (applies to deliverables 1-4)

Each of the four tool reports must cover these dimensions with equal depth:

1. Overview and positioning — What is the tool? Who is it for? What problem does it solve? How mature is it?
2. Workflow orchestration model — How does it manage multi-step tasks? Sequential vs parallel execution? State management? Session persistence?
3. Agent/persona architecture — Does it use multiple agents/roles? How are they defined? How do they communicate? Can users add custom personas?
4. UX and developer experience — How does the user interact with it? CLI, GUI, chat? How much configuration is needed? What does the feedback loop look like?
5. Extensibility and customization — Plugin system? Configuration files? Hooks? Can users extend or override behavior?
6. Reliability and error handling — How does it handle failures? Retries? Partial completion? Context window limits?
7. Git integration and code isolation — Does it use branches, worktrees, or other isolation? How are changes staged, reviewed, and merged?
8. Strengths and weaknesses summary — Bullet-point summary of what the tool does well and where it falls short

### Gap Analysis Structure (deliverable 5)

1. Feature comparison matrix — A table with all 4 tools + claude-split as columns, and capabilities across all 6 analysis dimensions as rows. Use notation: full support / partial / absent / N/A.
2. Identified gaps — Each gap as a section with: what capability claude-split lacks, which tool(s) demonstrate it, how they implement it.
3. High-value gaps — Subset flagged as high-priority with: why it is high-value, a concrete recommendation, estimated complexity (small / medium / large).
4. Lower-priority gaps — Remaining gaps for awareness, with one-line rationale for deprioritization.

## Constraints

- All analysis based on publicly available information (documentation, README files, source code on GitHub, blog posts, demo videos).
- Reports factual and specific. No vague claims without citing concrete features.
- Each report self-contained and readable independently.
- Gap analysis depends on all four reports being complete first.
- Use web research to gather information. Note information gaps explicitly rather than speculating.

## Acceptance Criteria

- All 5 documents exist in docs/competitive-analysis/
- Each of the 4 tool reports covers all 8 dimensions with substantive analysis
- Gap analysis includes a feature comparison matrix covering all tools and all dimensions
- At least 3 high-value gaps identified with concrete, actionable recommendations
- Lower-priority gaps listed with rationale for deprioritization
- Reports cite specific features, not vague impressions
- Each report is self-contained
- No speculative claims — information gaps noted as such

## Ticket Breakdown

| Ticket | Persona | Title | Depends on |
|--------|---------|-------|------------|
| T001 | Researcher | Factory Droid Missions report | — |
| T002 | Researcher | Superpowers plugin report | — |
| T003 | Researcher | Paperclip AI report | — |
| T004 | Researcher | Gastown report | — |
| T005 | Tech Lead | Gap analysis synthesis | T001, T002, T003, T004 |
| T006 | Verifier | Review all reports for completeness | T005 |

T001-T004 run in parallel. T005 requires all four complete. T006 verifies the full set.

### Complexity: Medium — 6 tickets, single milestone.