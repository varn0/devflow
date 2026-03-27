## Feature: Update Skills to Match Current bd CLI

### Overview

Update the `start-task`, `close-task`, and `architect` skills/agent to fix outdated `bd` CLI references, remove incorrect assumptions about storage (manual `.beads/` git commits), and leverage newer `bd` features (`--suggest-next`, `bd prime`, `bd create --parent` for task trees).

### Components Affected

- [x] `skills/start-task/SKILL.md` — fix prerequisites, add `bd prime`
- [x] `skills/close-task/SKILL.md` — remove `.beads/` git commits, add `--suggest-next`, add next-work suggestion
- [x] `agents/architect.md` — add implementation task creation in `bd` after spec is written

### Changes by File

#### `skills/start-task/SKILL.md`

**Prerequisites Check (replace current):**
1. Check `which bd` — if not found, tell user to install bd (do not auto-install; Dolt dependency makes this non-trivial).
2. Check bd is operational: `bd info --json` — if it fails, tell user to run `bd init` or start the Dolt server.
3. Remove: `npm install -g @beads/bd` auto-install suggestion.
4. Remove: `ls .beads/` check and `bd init` auto-run.

**Step changes:**
- Steps 1-5 (rebase, ready, show, claim, branch): keep as-is, commands are correct.
- Step 6 (check for linked spec): also check `bd show` output for a `design` field, not just `spec_id`.
- New Step 7: after claiming, run `bd prime` to get AI-optimized project context. Display relevant info to inform planning in plan mode.
- Step 8 (enter plan mode): renumbered, otherwise unchanged.

#### `skills/close-task/SKILL.md`

**Step 1 (Find the task):** Keep as-is. `bd show --current --json` is correct.

**Step 2 (Show the task):** Keep as-is.

**Step 3 (Close the task):** Change command to:
```bash
bd close <id> -r "<reason>" --suggest-next --json
```
- Use short flag `-r` (stylistic consistency).
- Add `--suggest-next` to surface newly unblocked issues.

**Step 4 (Commit .beads/ changes):** Remove entirely. bd uses Dolt — no manual git commits of `.beads/` needed. Replace with: if there are uncommitted working-tree changes (code files, not `.beads/`), remind the user to commit their implementation work.

**New Step 5 (Next work suggestion):** Parse `--suggest-next` output from step 3. If newly unblocked tasks exist, display them and ask the user if they want to start one (which would be a `/start-task` invocation).

#### `agents/architect.md`

**New prerequisite check (top of agent):**
- At the start, check `which bd && bd info --json`. Store result — bd may or may not be available.
- If bd is not available, the agent works normally but skips the task creation step.

**New step 6.5: "Create implementation tasks in bd" (between "Write spec document" and "Spec review loop"):**
- Only runs if bd is available (best-effort, not a gate).
- Parse the `### Implementation Plan` section of the written spec.
- If the work has multiple phases/tasks:
  1. Create a parent issue (epic): `bd create "<feature name>" -d "<overview>" --design-file <spec-path> --json`
  2. For each task in the plan: `bd create "<task title>" -d "<description>" --parent <epic-id> --json`
  3. Set ordering dependencies: `bd dep add <id> blocks <id>` where the spec indicates sequencing.
- If the work is a single task, create one issue with `--design-file` pointing to the spec.
- Display the created task tree to the user for confirmation.
- Add note to checklist item 6 in the agent: "6. Write spec document and create bd tasks (if bd is available)"

**Checklist update:** Add task creation as part of step 6 (not a separate step, to keep it optional/conditional).

### What Does NOT Change

- `skills/architect/SKILL.md` — thin dispatcher, no changes needed.
- Branch naming conventions in `start-task`.
- The "What This Skill Does NOT Do" section in `close-task` (still accurate).
- The architect agent's core process flow (questions, approaches, design, spec, review).
- No new skills or agents are created.

### CLAUDE.md Updates

No updates required. The CLAUDE.md already describes the plugin structure and mentions `bd` CLI usage. The changes are internal to skill/agent files and don't introduce new patterns or conventions.

### Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `bd info` may fail in projects without Dolt server running | Skills give clear error message with fix instructions, don't auto-run destructive commands |
| `bd prime` output format may vary | Treat as informational context, don't parse programmatically |
| Architect task creation may fail mid-way (some issues created, some not) | Display what was created so far, let user decide how to proceed |
| `--suggest-next` output format may change | Parse with `--json` flag, handle gracefully if empty |
