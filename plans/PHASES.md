# Build Phases

Tracks the active and planned development phases of the agentic-fm vision. Each phase maps to one or more skills from `VISION.md` and lives in its own git worktree.

## Worktree conventions

- Worktrees are created under `/worktrees/` inside the container, which maps to `./worktrees/agentic-fm/` on the host.
- Branch naming: `feature/{phase-slug}`
- Worktree path: `/worktrees/{phase-slug}`

```bash
# Create a worktree for a phase
git worktree add /worktrees/schema-build feature/schema-build

# List active worktrees
git worktree list

# Remove a worktree after merge
git worktree remove /worktrees/schema-build
```

---

## Phase status legend

| Symbol | Meaning |
|---|---|
| `planned` | Scoped in VISION.md, not yet started |
| `active` | Worktree exists, work in progress |
| `merged` | Branch merged to main, worktree removed |

---

## Phase 1 — Layout Design & XML2 Generation

**Status**: `planned`
**Branch**: `feature/layout-design`
**Worktree**: `/worktrees/layout-design`
**Vision ref**: Tooling Infrastructure → Layout Object Reference; Skills → `layout-design`, `layout-spec`, `webviewer-build`

**Scope**:
- Complete the `layout-design` skill — design conversation, XML2 object generation, clipboard load
- Complete the `layout-spec` skill — written blueprint output for manual builds
- Complete the `webviewer-build` skill — full HTML/CSS/JS web viewer app + FM bridge scripts
- Validate XML2 output format against `xml_parsed/` layout exports from a real solution

**Explicitly out of scope**: Layout container creation (permanently manual), responsive design for native FM layouts.

---

## Phase 2 — OData Schema Tooling

**Status**: `planned`
**Branch**: `feature/schema-tooling`
**Worktree**: `/worktrees/schema-tooling`
**Vision ref**: Tooling Infrastructure → Field Definition and Schema Reference; Skills → `schema-plan`, `schema-build`, `relationship-spec`, `odata-connect`

**Scope**:
- Complete the `odata-connect` skill — Docker-hosted FM Server setup walkthrough
- Complete the `schema-plan` skill — ERD as Mermaid in `plans/schema/`, extended to FM table occurrences
- Complete the `schema-build` skill — OData REST calls to create tables and fields transactionally
- Complete the `relationship-spec` skill — precise click-through checklist for the developer
- Validate OData field type mappings against live FM Server responses

**Explicitly out of scope**: Relationship creation via API (permanently manual).

---

## Phase 3 — Multi-Script Scaffold

**Status**: `planned`
**Branch**: `feature/multi-script`
**Worktree**: `/worktrees/multi-script`
**Vision ref**: What Makes This Hard → Untitled Placeholder Technique; Skills → `multi-script-scaffold`

**Scope**:
- Implement the `multi-script-scaffold` skill — calculate placeholder count, guide creation, capture IDs via Push Context, generate all scripts in one pass with correct Perform Script wiring, walk developer through renames
- Integrate with `context-refresh` to capture Untitled script IDs before generation
- Test against a 3-script and a 5-script interdependent system

---

## Phase 4 — Script Tooling Expansion

**Status**: `planned`
**Branch**: `feature/script-tooling`
**Worktree**: `/worktrees/script-tooling`
**Vision ref**: Skills → `script-refactor`, `script-test`, `script-debug`, `implementation-plan`

**Scope**:
- Complete the `script-refactor` skill
- Complete the `script-test` skill — companion verification script via `fm-debug`
- Complete the `script-debug` skill — systematic reproduce/isolate/fix workflow
- Complete the `implementation-plan` skill — decompose requirements before generation

---

## Phase 5 — Solution-Level Skills

**Status**: `planned`
**Branch**: `feature/solution-level`
**Worktree**: `/worktrees/solution-level`
**Vision ref**: Skills → `solution-blueprint`, `solution-audit`, `solution-docs`, `function-create`, `privilege-design`

**Scope**:
- Complete the `solution-blueprint` skill — full ordered build sequence from plain-English description
- Complete the `solution-audit` skill — technical debt, naming, anti-pattern analysis
- Complete the `solution-docs` skill — auto-generated documentation from xml_parsed
- Complete the `function-create` skill — custom function generation
- Complete the `privilege-design` skill — privilege sets and account structure

---

## Phase 6 — Web Migration

**Status**: `planned`
**Branch**: `feature/migrate-web`
**Worktree**: `/worktrees/migrate-web`
**Vision ref**: Tooling Infrastructure → Migration Tooling; Skills → `migrate-out`

**Scope**:
- Complete the `migrate-out` skill — DDR XML → SQL schema, REST API design, UI component specs
- Build on and extend the `migrate-filemaker` open-source foundation
- Develop opinionated patterns for React + Supabase and Next.js full-stack target stacks
- WebDirect HTML capture as supplementary UI reference

---

## Phase 7 — Data Tooling

**Status**: `planned`
**Branch**: `feature/data-tooling`
**Worktree**: `/worktrees/data-tooling`
**Vision ref**: Skills → `data-seed`, `data-migrate`

**Scope**:
- Complete the `data-seed` skill — realistic seed/test data via OData
- Complete the `data-migrate` skill — external source → FM via OData with field mapping and type coercion

---

## Phase 8 — Native & Inbound Migration

**Status**: `planned`
**Branch**: `feature/migrate-native-in`
**Worktree**: `/worktrees/migrate-native-in`
**Vision ref**: Skills → `migrate-native`, `migrate-in`

**Scope**:
- Complete the `migrate-native` skill — FM layout XML → SwiftUI/UIKit Xcode project
- Complete the `migrate-in` skill — SQL DDL / ORM / spreadsheet → FM via OData + clipboard
