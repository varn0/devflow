# Update Skills to Match Current bd CLI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix outdated bd CLI references in start-task, close-task skills and add bd task creation to the architect agent.

**Architecture:** Three independent file edits — each skill/agent file is self-contained. No shared state between tasks. Edit in any order.

**Tech Stack:** Markdown skill/agent definitions, bd CLI

**Spec:** `docs/specs/2026-03-27-update-skills-bd-cli-design.md`

---

### Task 1: Update `start-task` skill prerequisites and add `bd prime`

**Files:**
- Modify: `skills/start-task/SKILL.md`

- [ ] **Step 1: Replace the Prerequisites Check section**

Replace the entire `## Prerequisites Check` section (lines 10-31) with:

```markdown
## Prerequisites Check

Before anything else, verify the toolchain:

1. **Check if `bd` is installed:**
   ```bash
   which bd
   ```
   If not found, tell the user to install bd. Do NOT auto-install — bd requires a Dolt server, making installation non-trivial.

2. **Check bd database is discoverable:**
   ```bash
   bd info --json
   ```
   If this fails, the `.beads/*.db` file is missing or corrupted. Tell the user to run `bd init` or check their Dolt server is running.
   Note: this checks for a valid database file, not Dolt server connectivity.
```

- [ ] **Step 2: Update step 6 (check for linked spec)**

Replace the full line for step 6. Current line:
```
6. **Check for a linked spec** — if the task has a `spec_id` field or mentions a spec path, read that file.
```
Replace with:

```markdown
6. **Check for a linked spec** — inspect the `bd show` JSON output:
   - Check for a `design` field first. If present, read that file.
   - Fall back to `spec_id` if `design` is absent. If present, read that file.
   - If neither exists, proceed without a spec.
```

- [ ] **Step 3: Add new step 7 (bd prime) and renumber existing step 7 to step 8**

First, rename the existing step 7 heading from `7. **Enter plan mode**` to `8. **Enter plan mode**`.

Then, insert the following new step 7 between step 6 and the renumbered step 8:

```markdown
7. **Load project context** — run `bd prime` to get AI-optimized workflow context:
   ```bash
   bd prime
   ```
   Review the output for relevant project state (open blockers, related issues, recent activity). Use this context to inform the implementation plan in plan mode.

8. **Enter plan mode** — use `EnterPlanMode` to begin planning the implementation:
   - Read the spec (if one exists) and relevant source files
   - Understand the current codebase state for affected areas
   - Design the implementation approach
   - Present a step-by-step plan for user approval
```

- [ ] **Step 4: Review the full file for correctness**

Read the modified file end-to-end. Verify:
- Prerequisites section has exactly 2 checks (which bd, bd info)
- No references to `npm install -g @beads/bd`
- No references to `ls .beads/` or `bd init` auto-run
- Steps numbered 1-8 with no gaps
- `bd prime` is step 7

- [ ] **Step 5: Commit**

```bash
git add skills/start-task/SKILL.md
git commit -m "fix(start-task): update prerequisites and add bd prime context"
```

---

### Task 2: Update `close-task` skill — remove .beads/ commits, add --suggest-next

**Files:**
- Modify: `skills/close-task/SKILL.md`

- [ ] **Step 1: Update step 3 (close command)**

Replace the step 3 command block. Current:
```markdown
3. **Close the task** with a reason:
   ```bash
   bd close <id> --reason "<short description of what was done>" --json
   ```
   Derive the reason from the work completed (commit messages, branch name, or user input).
```

New:
```markdown
3. **Close the task** with a reason:
   ```bash
   bd close <id> -r "<short description of what was done>" --suggest-next --json
   ```
   Derive the reason from the work completed (commit messages, branch name, or user input).
   The `--suggest-next` flag causes the JSON output to include any newly unblocked issues.
```

- [ ] **Step 2: Replace step 4 (remove .beads/ git commits)**

Replace the entire step 4. Current step commits `.beads/` changes. New step:

```markdown
4. **Check for uncommitted work** — remind the user to commit implementation changes:
   ```bash
   git status
   ```
   If there are uncommitted working-tree changes (code files), remind the user to commit their implementation work before moving on. Do NOT commit `.beads/` directory changes — bd uses Dolt for its own state management.
```

- [ ] **Step 3: Add new step 5 (next work suggestion)**

After step 4, add:

```markdown
5. **Suggest next work** — if the `bd close` JSON output from step 3 contains a non-empty list of newly unblocked issues, display them:
   - Show each issue's ID, title, and priority.
   - Ask the user if they want to start one of these tasks (which would be a `/start-task` invocation).
   - If no newly unblocked issues, skip this step silently.
```

- [ ] **Step 4: Review the full file for correctness**

Read the modified file end-to-end. Verify:
- Step 3 uses `-r` and `--suggest-next`
- No references to `git add .beads/` or committing `.beads/` files
- Steps numbered 1-5 with no gaps
- "What This Skill Does NOT Do" section is unchanged

- [ ] **Step 5: Commit**

```bash
git add skills/close-task/SKILL.md
git commit -m "fix(close-task): remove .beads/ commits, add --suggest-next"
```

---

### Task 3: Add bd task creation to architect agent

**Files:**
- Modify: `agents/architect.md`

- [ ] **Step 1: Add bd availability check to step 1 description**

In the "Understanding the Problem" section (line 79), after the first bullet ("Check out the current project state first"), add a new bullet:

```markdown
- Check if `bd` is available for task tracking: run `which bd && bd info --json`. Note whether bd is operational — this determines whether implementation tasks can be created in bd later. If bd is not available, the agent works normally but skips task creation.
```

- [ ] **Step 2: Update checklist item 6**

Change checklist item 6 from:
```markdown
6. **Write spec document** — save to `docs/specs/` (or wherever the project keeps specs) and commit
```
to:
```markdown
6. **Write spec document and create bd tasks** — save spec to `docs/specs/` (or wherever the project keeps specs), commit, then create implementation tasks in bd (if bd is available — best-effort, not a gate)
```

- [ ] **Step 3: Add bd task creation instructions to "After the Design" section**

In the "After the Design" section, after the "Documentation" subsection (after "Commit the design document to git"), add:

```markdown
**Create implementation tasks in bd (if bd is available):**

If `bd` was detected as available in step 1, create trackable issues from the spec's Implementation Plan:

- If the work has multiple phases/tasks:
  1. Create a parent epic:
     ```bash
     bd create "<feature name>" -t epic -d "<overview>" --design-file <spec-path> --json
     ```
  2. For each task in the implementation plan:
     ```bash
     bd create "<task title>" -d "<description>" --parent <epic-id> --json
     ```
  3. Set ordering dependencies where the plan indicates sequencing:
     ```bash
     bd dep add <blocked-id> <blocker-id>
     ```
     (First arg depends on second arg. Example: `bd dep add bd-5 bd-4` means bd-5 is blocked by bd-4.)
- If the work is a single task, create one issue:
  ```bash
  bd create "<task title>" -d "<description>" --design-file <spec-path> --json
  ```
- Display the created task tree to the user for confirmation.
- If any `bd create` command fails mid-way, display what was created so far and let the user decide how to proceed.
- If bd is not available, skip this section entirely — it is best-effort, not a gate.
```

- [ ] **Step 4: Review the full file for correctness**

Read the modified file end-to-end. Verify:
- Checklist item 6 mentions bd tasks
- "Understanding the Problem" section includes bd availability check
- "After the Design" section has bd task creation between "Documentation" and "Spec Review Loop"
- The `dot` flow diagram is unchanged
- No other checklist items or sections were modified

- [ ] **Step 5: Commit**

```bash
git add agents/architect.md
git commit -m "feat(architect): add bd task creation from spec implementation plan"
```
