# Agent Team Implementation Plan

How to execute the agentic-fm build phases using parallel agent teams to minimise elapsed time.

---

## Dependency graph

```
Phase 1 (Layout)      ─┐
Phase 2 (OData)       ─┤
Phase 3 (Multi-Script) ┤──► Phase 5 (Solution-Level)
Phase 4 (Script Tools) ┤
Phase 6 (Web Migration)┘

Phase 2 (OData) ───────────► Phase 7 (Data Tooling)

Phase 1 + Phase 2 ─────────► Phase 8 (Native & Inbound)
```

Phases 1, 2, 3, 4, and 6 have no meaningful dependencies on each other. These form Wave 1 and run fully in parallel.

---

## Wave structure

### Wave 1 — 5 agents in parallel

| Agent | Phase | Branch | Worktree | Key risk |
|---|---|---|---|---|
| A | Phase 1 — Layout & XML2 | `feature/layout-design` | `/worktrees/layout-design` | XML2 format validation requires real FM paste testing |
| B | Phase 2 — OData Schema | `feature/schema-tooling` | `/worktrees/schema-tooling` | Requires live FM Server for OData validation |
| C | Phase 3 — Multi-Script Scaffold | `feature/multi-script` | `/worktrees/multi-script` | Tight integration with Push Context — interface spec must be locked first |
| D | Phase 4 — Script Tooling | `feature/script-tooling` | `/worktrees/script-tooling` | `script-test` depends on `fm-debug` being stable |
| E | Phase 6 — Web Migration | `feature/migrate-web` | `/worktrees/migrate-web` | Mostly research and prompting work — lowest FM dependency |

### Wave 2 — launch opportunistically as Wave 1 phases merge

| Agent | Phase | Branch | Worktree | Depends on |
|---|---|---|---|---|
| F | Phase 5 — Solution-Level | `feature/solution-level` | `/worktrees/solution-level` | All of Wave 1 |
| G | Phase 7 — Data Tooling | `feature/data-tooling` | `/worktrees/data-tooling` | Phase 2 only — launch as soon as B merges |
| H | Phase 8 — Native & Inbound | `feature/migrate-native-in` | `/worktrees/migrate-native-in` | Phases 1 + 2 |

---

## Setup: worktrees and branches

Run these commands from the repository root before launching any agents. Each command creates the branch and checks it out in its own isolated worktree.

```bash
# Wave 1
git worktree add /worktrees/layout-design -b feature/layout-design
git worktree add /worktrees/schema-tooling -b feature/schema-tooling
git worktree add /worktrees/multi-script -b feature/multi-script
git worktree add /worktrees/script-tooling -b feature/script-tooling
git worktree add /worktrees/migrate-web -b feature/migrate-web

# Wave 2 (create when ready to launch)
git worktree add /worktrees/solution-level -b feature/solution-level
git worktree add /worktrees/data-tooling -b feature/data-tooling
git worktree add /worktrees/migrate-native-in -b feature/migrate-native-in
```

Verify all worktrees:

```bash
git worktree list
```

Remove a worktree after its branch is merged:

```bash
git worktree remove /worktrees/{phase-slug}
```

---

## Prerequisites before launching Wave 1

These must be in place before agents start work. Doing this after agents begin risks incompatible assumptions baked into skill files.

1. **`plans/SKILL_INTERFACES.md` is final** — every agent reads this before authoring any skill that calls or is called by another skill. The interface contracts (inputs, outputs, calls, called-by) define the seams between skills.

2. **Shared infrastructure is locked** — the following files must not be modified by any agent without coordinator approval. Changes here affect every other agent's work:
   - `agent/scripts/clipboard.py`
   - `agent/scripts/validate_snippet.py`
   - `agent/catalogs/step-catalog-en.json`
   - `.claude/CLAUDE.md`
   - Companion server endpoints

3. **`fm-debug` skill is stable** — Phase 4's `script-test` skill depends on it. Confirm the current `fm-debug` implementation is production-ready before Agent D starts.

4. **Invoice Solution XML is current** — Phase 1 (XML2 generation) validates against `xml_parsed/` layout exports. Run `solution-export` to ensure these are up to date before Agent A begins.

---

## Agent prompts

Each agent should be launched with a prompt containing:
1. The full `plans/VISION.md`
2. The phase scope from `plans/PHASES.md` for their specific phase
3. `plans/SKILL_INTERFACES.md`
4. Instruction to read `agent/docs/CODING_CONVENTIONS.md` and the relevant sections of `.claude/CLAUDE.md` before producing any output
5. The constraint: do not modify shared infrastructure files (listed above)

### Agent A — Layout & XML2

> You are building Phase 1 of the agentic-fm project. Your scope is: the `layout-design`, `layout-spec`, and `webviewer-build` skills. Read `plans/VISION.md` (Layout Objects section and Tooling Infrastructure → Layout Object Reference), `plans/SKILL_INTERFACES.md`, and the existing skill files in `.claude/` for format reference. Produce skill markdown files. Validate XML2 output against `agent/xml_parsed/` layout exports. Do not modify shared infrastructure files.

### Agent B — OData Schema

> You are building Phase 2 of the agentic-fm project. Your scope is: the `odata-connect`, `schema-plan`, `schema-build`, and `relationship-spec` skills. Read `plans/VISION.md` (API-Managed Schema section), `plans/SKILL_INTERFACES.md`, and existing skill files for format reference. Document OData field type mappings. Do not modify shared infrastructure files.

### Agent C — Multi-Script Scaffold

> You are building Phase 3 of the agentic-fm project. Your scope is: the `multi-script-scaffold` skill. Read `plans/VISION.md` (Untitled Placeholder Technique section), `plans/SKILL_INTERFACES.md`, and existing skill files for format reference. The skill must integrate with `context-refresh` per the interface spec. Test against a 3-script and a 5-script interdependent scenario. Do not modify shared infrastructure files.

### Agent D — Script Tooling

> You are building Phase 4 of the agentic-fm project. Your scope is: the `script-refactor`, `script-test`, `script-debug`, and `implementation-plan` skills. Read `plans/VISION.md` (Skills section), `plans/SKILL_INTERFACES.md`, and existing skill files for format reference. `script-test` must use `fm-debug` per the interface spec. Do not modify shared infrastructure files.

### Agent E — Web Migration

> You are building Phase 6 of the agentic-fm project. Your scope is: the `migrate-out` skill. Read `plans/VISION.md` (Migrations → Migrating Out of FileMaker and Migration Tooling sections), `plans/SKILL_INTERFACES.md`, and the `migrate-filemaker` open-source project as a starting reference. Develop opinionated patterns for React + Supabase and Next.js target stacks. Do not modify shared infrastructure files.

---

## The human bottleneck: FM validation

Agents can produce skill files and fmxmlsnippet artifacts autonomously. They cannot validate them in FileMaker. This creates a testing queue that runs alongside the agent wave.

**Handling it**:
- Each agent flags artifacts as ready for FM validation when produced
- The agent continues with non-FM-dependent work (prompt logic, edge cases, documentation) rather than blocking
- FM validation is batched — paste and verify each artifact as it becomes available, not all at once at the end

**Validation checklist per skill**:
- [ ] Trigger phrases invoke the skill correctly
- [ ] Generated fmxmlsnippet passes `validate_snippet.py`
- [ ] Clipboard write succeeds without corruption
- [ ] Pasted result appears correctly in the target FM workspace (Script Workspace, Manage Database, Layout Mode)
- [ ] Generated FM objects behave as expected at runtime

---

## Merge and integration sequence

1. Phase 6 (Web Migration) is lowest-risk — merge first if ready; no other phase depends on it
2. Phase 3 (Multi-Script) is largely self-contained — merge second
3. Phases 1, 2, 4 — merge as validated; no ordering constraint between them
4. Phase 7 — launch Agent G as soon as Phase 2 merges; it only needs OData connectivity
5. Phase 8 — launch Agent H once Phases 1 and 2 are both merged
6. Phase 5 (Solution-Level) — launch Agent F only after all other Wave 1 phases are merged and stable; it calls every other skill

---

## Coordinator responsibilities

One human (or a dedicated coordinator agent on `main`) should own:

- Approving any proposed changes to locked shared infrastructure files
- Reviewing and merging PRs in the sequence above
- Tracking the FM validation queue and unblocking agents when validation results are ready
- Updating `plans/PHASES.md` status (`planned` → `active` → `merged`) as work progresses
- Resolving any interface contract disagreements between agents before they diverge

---

## Risk register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agents make incompatible interface assumptions | High without prep | High | Lock `SKILL_INTERFACES.md` before launch |
| Shared infrastructure conflicts between agents | Medium | High | Lock list enforced; all infra changes routed through coordinator |
| FM validation bottleneck delays merge | High | Medium | Agents continue non-FM work while validation queues; batch paste sessions |
| XML2 format assumptions incorrect | Medium | Medium | Agent A validates against `xml_parsed/` before finalising skill |
| OData API behaviour differs from documentation | Medium | Medium | Agent B documents deviations in `plans/schema/odata-notes.md` |
| `fm-debug` instability blocks Phase 4 | Low | Medium | Confirm fm-debug stability before launching Agent D |
