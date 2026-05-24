# verify-spec Skill Design

## Overview

A new `/verify-spec` skill that reads a spec's Verification Plan and orchestrates a structured pass through each check — dispatching to Playwright (via `/visual-qa`) for visual items and walking the user through behavioral/edge-case items as an interactive checklist. This also requires adding a "Verification Plan" section to the architect agent's spec template so that every spec ships with verifiable acceptance criteria.

## Components Affected

- `agents/architect.md` — add Verification Plan section to the spec template and design workflow
- `skills/verify-spec/SKILL.md` — new skill file
- `hooks/session-context.md` — add `/verify-spec` to the available skills table
- `CLAUDE.md` — add `verify-spec` to the project structure listing

## Changes by File

### `agents/architect.md`

**Spec Document Structure (add new section):**

Add a `### Verification Plan` section to the spec template. This section appears after `### Implementation Plan` and before `### CLAUDE.md Updates`. Structure:

```markdown
### Verification Plan

#### Visual Checks
<!-- Items verifiable via Playwright screenshots. Omit section if no UI is involved. -->
- [ ] [description of what to screenshot and what to look for]

#### Behavioral Checks
<!-- Non-visual verification: API responses, CLI output, data correctness, state transitions. -->
- [ ] [description of what to test and expected outcome]

#### Edge Cases
<!-- Boundary conditions to verify. -->
- [ ] [description of edge case and expected behavior]
```

**Design workflow guidance:**

When designing the Verification Plan, the architect should consider:
- Visual checks are only relevant for features with UI components. If the feature is purely backend/CLI/infrastructure, omit the Visual Checks sub-section entirely.
- Each check item should be specific enough that a pass/fail judgment is unambiguous.
- Behavioral checks should describe both the action to perform and the expected outcome.
- Edge cases should describe the boundary condition, how to trigger it, and expected behavior.

### `skills/verify-spec/SKILL.md`

New file at `skills/verify-spec/SKILL.md`.

**Frontmatter:**

```yaml
---
name: verify-spec
description: Verify a completed feature against its spec's Verification Plan. Runs visual checks via Playwright and walks through behavioral/edge-case checks interactively.
user-invocable: true
argument-hint: [path to spec file]
---
```

**Skill body — core flow:**

#### Step 1: Locate the spec

- If `$ARGUMENTS` contains a file path, use that spec.
- If `$ARGUMENTS` is empty or not a path, discover the most recent spec:
  - Glob for `docs/specs/*.md` (or the project's spec directory if different).
  - Sort by filename (specs are date-prefixed per convention).
  - Pick the most recent one.
  - Show the user which spec was selected and ask for confirmation before proceeding.

#### Step 2: Extract the Verification Plan

- Read the spec file.
- Look for a `### Verification Plan` section (or `## Verification Plan`).
- If no Verification Plan is found, tell the user this spec has no verification plan and stop. Do not improvise checks.
- Parse the plan into three lists: Visual Checks, Behavioral Checks, Edge Cases.
- Each list may be empty (e.g., a backend feature has no visual checks). Skip empty sections silently.

#### Step 3: Runtime capability detection

Before running checks, detect what tools are available:

- **Playwright availability**: Check if the Playwright MCP server is connected by attempting to list available MCP tools matching `playwright` or `browser`. If Playwright is not available and there are visual checks, inform the user: "Visual checks require Playwright MCP. These will be converted to manual checks." Then treat visual checks as behavioral checks (the user verifies them manually).
- No other external dependencies are required. Behavioral and edge-case checks are always available since they are human-judged.

#### Step 4: Run Visual Checks (if any)

For each visual check item:

1. Announce the check being performed.
2. Dispatch to the visual-qa approach: take Playwright screenshots at the relevant viewpoints/states described in the check item.
3. Present the screenshots to the user.
4. Ask the user: "Does this look correct? (pass / fail / skip)"
5. Record the result.

If Playwright is unavailable, present the check description and ask the user to verify manually (same pass/fail/skip prompt).

#### Step 5: Run Behavioral Checks (if any)

For each behavioral check item:

1. Announce the check.
2. If the check describes a concrete action Claude can perform (run a command, call an API, check a file), do it and show the output.
3. Present the expected outcome alongside the actual result.
4. Ask the user: "Pass, fail, or skip?"
5. Record the result.

The key principle: Claude assists by executing what it can, but the human makes the pass/fail judgment. Claude does not auto-pass anything.

#### Step 6: Run Edge Case Checks (if any)

Same flow as behavioral checks. These are separated in the spec for clarity but follow the identical execution pattern during verification.

#### Step 7: Report Summary

After all checks are complete, display a summary table:

```
## Verification Summary

Spec: docs/specs/2026-05-24-some-feature-design.md

| Category    | Total | Passed | Failed | Skipped |
|-------------|-------|--------|--------|---------|
| Visual      |     3 |      2 |      1 |       0 |
| Behavioral  |     5 |      4 |      0 |       1 |
| Edge Cases  |     2 |      2 |      0 |       0 |
| **Total**   |**10** |  **8** |  **1** |   **1** |

### Failed Checks
- [Visual] Login form alignment on mobile viewport — user reported misalignment on 375px width
```

If all checks pass: "All checks passed. Feature is verified against spec."

If any checks failed, list them with the category and any notes.

**Results are ephemeral** — shown in the session only, not persisted to any file.

### `hooks/session-context.md`

Add one row to the Available Skills table:

```
| `/verify-spec` | Verify a feature against its spec's Verification Plan |
```

### `CLAUDE.md`

Update the project structure listing:

```
skills/           /architect, /start-task, /close-task, /merge-workspace, /visual-qa, /verify-spec
```

## Data Flow

```
User invokes /verify-spec [spec-path]
        |
        v
  Locate spec file (argument or most-recent discovery)
        |
        v
  Parse Verification Plan section
        |
        v
  Detect Playwright availability
        |
        +-- Visual checks -----> Playwright MCP (screenshots) ---> User judges pass/fail
        |                         (or manual if no Playwright)
        |
        +-- Behavioral checks --> Claude executes actions ---------> User judges pass/fail
        |
        +-- Edge case checks ---> Claude executes actions ---------> User judges pass/fail
        |
        v
  Aggregate results into summary table
        |
        v
  Display summary (ephemeral, in-session only)
```

## Design Decisions and Rationale

**Why semi-automated, not fully automated?**
Fully automated verification requires machine-readable assertions, which would make the spec format rigid and project-specific. The semi-automated approach keeps specs human-readable and works for any project type — web UI, CLI tool, API, infrastructure.

**Why ephemeral results?**
Verification is a point-in-time activity. Persisting results creates stale artifacts that need maintenance. The user can copy the summary into an issue comment or MR description if they want a record.

**Why dispatch to visual-qa instead of reimplementing Playwright logic?**
visual-qa is the existing low-level Playwright screenshot tool. verify-spec is an orchestrator that adds structure (which checks, in what order, with what judgment). This follows the single-responsibility principle and avoids duplicating Playwright interaction logic.

**Why not auto-pass behavioral checks?**
Even when Claude can execute a command and see the output matches expectations, the human should confirm. This prevents false confidence from brittle string matching or misunderstood requirements. Claude assists; the human decides.

## Implementation Plan

### Phase 1: Core (MVP)

1. Add the `### Verification Plan` section to the spec template in `agents/architect.md`.
2. Create `skills/verify-spec/SKILL.md` with the full skill flow (steps 1-7).
3. Update `hooks/session-context.md` with the new skill entry.
4. Update `CLAUDE.md` project structure listing.

Single-phase feature. The skill is self-contained, has no external dependencies beyond the optional Playwright MCP, and follows established patterns.

### Future Enhancements (not in scope)

- Structured output format (JSON) for CI integration — only if a real need emerges.
- Auto-detection of testable assertions from spec language — risks over-engineering.
- Integration with issue tracker (auto-comment verification results on the issue) — nice-to-have, not MVP.

## CLAUDE.md Updates

Update the `skills/` line in the project structure section to include `/verify-spec`.

## Open Questions

None — the design direction was pre-approved.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| Spec has no Verification Plan section | Skill detects this and stops with a clear message. Does not improvise checks. |
| Playwright MCP not available but spec has visual checks | Graceful degradation: visual checks become manual checks with the same pass/fail prompt. |
| Verification Plan items are vague or ambiguous | Architect agent guidance encourages specific, unambiguous check items. This is a human authoring quality issue, not a tooling problem. |
| User skips all checks | Summary still displays, showing everything as skipped. No false "verified" signal. |
| Spec format varies (h2 vs h3 for Verification Plan) | Skill checks for both `## Verification Plan` and `### Verification Plan`. |
