---
name: start-task
description: Rebase from main, find a ready task in beads (bd), claim it, create a branch, and enter plan mode to start implementation.
user-invocable: true
argument-hint: [task ID or description from bd ready]
---

Start implementing a task tracked by beads (`bd` CLI).

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

## Steps

1. **Rebase from local main** — bring the current branch up to date:
   ```bash
   git rebase main
   ```
   - Rebase against **local** `main` (not `origin/main`), since local main may have commits not yet pushed.
   - If conflicts occur, stop and inform the user. Do NOT force-resolve.

2. **Find a ready task** — use `bd ready` to list tasks with no open blockers:
   ```bash
   bd ready --json
   ```
   - If `$ARGUMENTS` is provided, match it against the ready list (by ID or title substring).
   - If multiple matches, show candidates and ask the user to pick.
   - If no match or no ready tasks, tell the user and stop.
   - If no argument was given, show the ready list and ask which task to start.

3. **Show task details** before claiming:
   ```bash
   bd show <id> --json
   ```
   Display: title, description, priority, dependencies, spec link (if any).

4. **Claim the task** — atomically set assignee + in_progress:
   ```bash
   bd update <id> --claim --json
   ```
   This is a single atomic command. Do NOT use separate assign + status update.

5. **Create a task branch** — checkout a new branch:
   - Derive a short kebab-case slug from the task title
   - Choose prefix based on task type/nature:
     - `feat/` — feature
     - `fix/` — bug
     - `build/` — build system, CI
     - `test/` — tests
     - `chore/` — maintenance, refactoring, docs
   - Create the branch: `git checkout -b <prefix>/<slug>`
   - If unsure which prefix, ask the user.

6. **Check for a linked spec** — inspect the `bd show` JSON output:
   - Check for a `design` field first. If present, read that file.
   - Fall back to `spec_id` if `design` is absent. If present, read that file.
   - If neither exists, proceed without a spec.

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
