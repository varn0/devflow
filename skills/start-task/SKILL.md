---
name: start-task
description: Use glab to list open GitLab issues, let user pick one, assign it, create a branch, and brainstorm the approach.
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

1. **Rebase from local main** — bring the current branch up to date:
   ```bash
   git rebase main
   ```
   - Rebase against **local** `main` (not `origin/main`), since local main may have commits not yet pushed.
   - If conflicts occur, stop and inform the user. Do NOT force-resolve.

2. **Find an open issue** — list available work:
   ```bash
   glab issue list --mine=false --assignee=none --per-page=20
   ```
   - If `$ARGUMENTS` is a number, fetch that issue directly:
     ```bash
     glab issue view <number>
     ```
   - If `$ARGUMENTS` is text, filter by title substring from the list.
   - If multiple matches, show candidates and ask the user to pick.
   - If no match or no open issues, tell the user and stop.
   - **If no argument was given**, display the issue list and ask the user which issue to start. Use `AskUserQuestion` to prompt for selection.

3. **Show issue details** before claiming:
   ```bash
   glab issue view <number>
   ```
   Display: title, description, labels, milestone, linked MRs (if any).

4. **Assign the issue** to yourself:
   ```bash
   glab issue update <number> --assignee @me
   ```

5. **Create a task branch** — checkout a new branch:
   - Derive a short kebab-case slug from the issue title
   - Include the issue number for traceability
   - Choose prefix based on issue labels or nature:
     - `feat/` — feature
     - `fix/` — bug
     - `build/` — build system, CI
     - `test/` — tests
     - `chore/` — maintenance, refactoring, docs
   - Create the branch: `git checkout -b <prefix>/<issue-number>-<slug>`
   - If unsure which prefix, ask the user.

6. **Check for linked design docs** — inspect the issue description:
   - Look for links to files in `docs/specs/` or `docs/plans/`
   - If found, read those files for context.
   - If no spec or design doc exists, ask the user: "No spec found for this issue. Would you like to create one before starting implementation?"
     - If yes, invoke the `/architect` skill to design the approach first.
     - If no, proceed to brainstorming.

7. **Brainstorm the approach** — invoke `superpowers:brainstorming` to explore:
   - What the issue requires
   - Relevant codebase areas and existing patterns
   - Implementation options and trade-offs
   - Follow the brainstorming skill's process to reach alignment with the user before writing code
