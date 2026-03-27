---
name: close-task
description: Mark a task as completed in beads (bd) and commit the change.
user-invocable: true
argument-hint: [task ID or description to mark as done]
---

Mark a task as completed in beads (`bd` CLI).

## Steps

1. **Find the task to close** — identify the beads issue:
   ```bash
   bd show --current --json
   ```
   - If `$ARGUMENTS` is a beads ID (e.g., `bd-a1b2`), use it directly.
   - If `$ARGUMENTS` is text, search for a matching in-progress task:
     ```bash
     bd list --status in_progress --json
     ```
     Match by substring. If multiple matches, show candidates and ask the user to pick.
   - If no argument, use `bd show --current` to find the active task.
   - If no match found, tell the user and stop.

2. **Show the task** for confirmation:
   ```bash
   bd show <id> --json
   ```
   Display title, status, and ask user to confirm this is the right task to close.

3. **Close the task** with a reason:
   ```bash
   bd close <id> -r "<short description of what was done>" --suggest-next --json
   ```
   Derive the reason from the work completed (commit messages, branch name, or user input).
   The `--suggest-next` flag causes the JSON output to include any newly unblocked issues.

4. **Check for uncommitted work** — remind the user to commit implementation changes:
   ```bash
   git status
   ```
   If there are uncommitted working-tree changes (code files), remind the user to commit their implementation work before moving on. Do NOT commit `.beads/` directory changes — bd uses Dolt for its own state management.

5. **Suggest next work** — if the `bd close` JSON output from step 3 contains a non-empty list of newly unblocked issues, display them:
   - Show each issue's ID, title, and priority.
   - Ask the user if they want to start one of these tasks (which would be a `/start-task` invocation).
   - If no newly unblocked issues, skip this step silently.

## What This Skill Does NOT Do

- **Does NOT merge branches** — that's the `merge-workspace` skill
- **Does NOT push to remote** — the user decides when to push
- **Does NOT delete branches** — branch cleanup is separate
- **Does NOT close child tasks** — only the specified task. If it has open children, `bd` will warn you.
