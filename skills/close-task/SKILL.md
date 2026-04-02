---
name: close-task
description: Wrap up work on a GitLab issue — commit, push, create MR. Issue closes automatically on MR merge.
user-invocable: true
argument-hint: [issue number or branch name]
---

Wrap up work on a GitLab issue and prepare it for merge.

Issues close automatically when the MR merges (via `Closes #N` in the MR description). This skill does NOT close issues manually.

## Steps

1. **Identify the issue** — determine which issue this work is for:
   - If `$ARGUMENTS` is a number, that's the issue number.
   - If on a branch like `feat/42-some-slug`, extract `42` as the issue number.
   - If ambiguous, ask the user.

2. **Check for uncommitted work:**
   ```bash
   git status
   ```
   If there are uncommitted changes, remind the user to commit before proceeding. Do NOT auto-commit — the user controls their commits.

3. **Push the branch:**
   ```bash
   git push -u origin HEAD
   ```

4. **Create a merge request** (if one doesn't already exist):
   - First check for an existing MR:
     ```bash
     glab mr list --head=$(git branch --show-current)
     ```
   - If no MR exists, create one:
     ```bash
     glab mr create --fill --assignee @me --title "<title>" --description "Closes #<issue-number>"
     ```
     - Derive the title from the branch name or issue title.
     - The `Closes #N` in the description ensures the issue auto-closes on merge.
     - If the project uses MR templates, `--fill` will pick them up.
   - If an MR already exists, show its URL and status.

5. **Suggest next work** — check for other open issues:
   ```bash
   glab issue list --assignee @me --per-page=5
   ```
   - If the user has other assigned issues, show them.
   - Otherwise, show unassigned issues:
     ```bash
     glab issue list --assignee=none --per-page=5
     ```
   - Ask if they want to start one (which would be a `/start-task` invocation).

## What This Skill Does NOT Do

- **Does NOT close issues** — issues close automatically when the MR merges (via `Closes #N`).
- **Does NOT merge branches** — that's the `merge-workspace` skill or the GitLab UI.
- **Does NOT delete branches** — GitLab can auto-delete source branches on merge.
