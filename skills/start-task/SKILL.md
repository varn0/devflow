---
name: start-task
description: List open GitLab issues, let user pick one, create a worktree with a task branch, rebase from main, and brainstorm the approach.
user-invocable: true
argument-hint: [issue number or title substring]
---

Start implementing a task tracked as a GitLab issue.

## Prerequisites Check

1. **Check if `glab` is installed and authenticated:**
   ```bash
   glab auth status
   ```
   If not found or not authenticated, tell the user to install/configure glab. Do NOT auto-install.

## Steps

1. **List open issues** — show all available work:
   ```bash
   glab issue list --per-page=20
   ```
   - If `$ARGUMENTS` is a number, fetch that issue directly:
     ```bash
     glab issue view <number>
     ```
   - If `$ARGUMENTS` is text, filter by title substring from the list.
   - If no match or no open issues, tell the user and stop.
   - **If no argument was given**, display the full issue list and ask the user which issue to start. Use `AskUserQuestion` to prompt for selection.

2. **Show issue details** — once the user picks an issue:
   ```bash
   glab issue view <number>
   ```
   Display: title, description, labels, milestone, linked MRs (if any).

3. **Assign the issue** to yourself:
   ```bash
   glab issue update <number> --assignee @me
   ```

4. **Note current position** — check which branch you're on:
   ```bash
   git branch --show-current
   ```

5. **Create a worktree with task branch** — use `superpowers:using-git-worktrees` to create an isolated workspace:
   - Derive a short kebab-case slug from the issue title
   - Include the issue number for traceability
   - Choose prefix based on issue labels or nature:
     - `feat/` — feature
     - `fix/` — bug
     - `build/` — build system, CI
     - `test/` — tests
     - `chore/` — maintenance, refactoring, docs
   - Branch name format: `<prefix>/<issue-number>-<slug>`
   - If unsure which prefix, ask the user.
   - The worktree skill handles directory selection and safety checks.

6. **Rebase from main** — inside the new worktree, bring up to date:
   ```bash
   git rebase main
   ```
   - Rebase against **local** `main` (not `origin/main`), since local main may have commits not yet pushed.
   - If conflicts occur, stop and inform the user. Do NOT force-resolve.

7. **Brainstorm the approach** — invoke `superpowers:brainstorming` to explore:
   - What the issue requires
   - Relevant codebase areas and existing patterns
   - Implementation options and trade-offs
   - If the issue description links to files in `docs/specs/` or `docs/plans/`, read those for context before brainstorming.
   - Follow the brainstorming skill's process to reach alignment with the user before writing code
