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

3. **Verify against spec** (if one exists):

   Check the issue for a spec reference:
   ```bash
   glab issue view <issue-number>
   ```
   - Look for a path to a spec file in the issue body (e.g., `docs/specs/2026-05-24-some-feature.md`).
   - If found, verify the file exists, then invoke `/verify-work <spec-path>`.
   - If verification fails, stop — the user should fix before proceeding.
   - If no spec is referenced in the issue, skip this step silently.

4. **Run unit tests** — gate the push on passing tests:

   **Detect what changed:**
   ```bash
   git diff --name-only main...HEAD
   ```

   **Classify changes as frontend, backend, or both** by inspecting the changed file paths. Do NOT hardcode path assumptions — discover the project layout:
   - Look for `package.json` files to identify frontend roots (commonly contain `react`, `next`, `vue`, `vite`, or `angular` in dependencies).
   - Look for backend markers: `pyproject.toml`, `go.mod`, `Cargo.toml`, `build.gradle`, `pom.xml`, or a `package.json` with `express`, `fastify`, `nestjs`, etc.
   - If the project is a monorepo, multiple roots may exist — classify by which root each changed file falls under.

   **Discover and run test commands:**
   - **Node/JS projects:** Check `package.json` `scripts` for `test`, `test:unit`, or similar. Run with `npm test` or `npx vitest run`, etc.
   - **Python projects:** Look for `pytest.ini`, `pyproject.toml [tool.pytest]`, or `setup.cfg`. Run `pytest`.
   - **Go projects:** Run `go test ./...` for changed packages.
   - **Other:** Look for a `Makefile` with a `test` target, or CI config for test commands.

   **Run only the relevant suite(s):**
   - Frontend changes only → run frontend tests only.
   - Backend changes only → run backend tests only.
   - Both → run both.
   - If no test framework is detected for a given area, warn the user and skip (don't block the push for missing tests).

   **If tests fail:** Show the output, ask the user how to proceed. Options:
   - Fix and re-run (do NOT auto-fix — the user controls the code).
   - Push anyway (user override — their call).

5. **Push the branch:**
   ```bash
   git push -u origin HEAD
   ```

6. **Create a merge request** (if one doesn't already exist):
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

7. **Suggest next work** — check for other open issues:
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
