---
name: implement-task
description: Use when starting work on a GitLab issue and taking it all the way through design to implementation. Triggers include picking up a tracked issue, "implement issue #N", "let's build the next task", or beginning feature work that needs design and a plan before coding.
user-invocable: true
argument-hint: [issue number or title substring]
---

Take a GitLab issue from selection through design, planning, and implementation.

## Overview

This skill orchestrates a full task pipeline: pick an issue, brainstorm the approach, optionally formalize it with the architect (spec), turn the spec/approach into a plan, implement, then wrap up (push + MR). Three stages are optional and chosen up front:

- **Architect review** — the `architect` skill produces and gets approval on a written spec.
- **Subagent-driven development** — the plan is executed via `superpowers:subagent-driven-development`.
- **Finish up** — when implementation is done, invoke the `close-task` skill to run the checks gate, push, and open the MR.

By default all three are ON. The user can turn any off at the start. The up-front "Finish up" choice is the authorization for the outward-facing push + MR, so the happy path runs hands-off from "code done" to "MR up" with no mid-flow prompt — while the failure gates inside `close-task` (failing checks or verification) still stop and ask.

## Prerequisites Check

**Check that `glab` is installed and authenticated:**
```bash
glab auth status
```
If not found or not authenticated, tell the user to install/configure `glab`. Do NOT auto-install.

## Steps

1. **Select the issue** — show available work and let the user pick:
   ```bash
   glab issue list --per-page=20
   ```
   - If `$ARGUMENTS` is a number, fetch it directly: `glab issue view <number>`.
   - If `$ARGUMENTS` is text, filter the list by title substring.
   - If no argument, display the list and ask which issue to start (`AskUserQuestion`).
   - If no match or no open issues, tell the user and stop.

2. **Show issue details** and assign it:
   ```bash
   glab issue view <number>
   glab issue update <number> --assignee @me
   ```
   Display title, description, labels, milestone, and linked MRs.

3. **Choose the execution mode** — ask this up front, before any design or implementation work begins. Use `AskUserQuestion`:

   > "Implement with defaults (architect review + subagent-driven development + finish up with push & MR), or change any of those options?"

   - **Defaults** → architect review ON, subagent-driven development ON, finish up ON.
   - **Change options** → ask a follow-up `AskUserQuestion` (multi-select): "Which stages should be enabled?" with options **Architect review**, **Subagent-driven development**, and **Finish up (push + MR)**. Enabled = selected; unselected = OFF.
     - If the resulting selection is surprising (e.g. architect **and** subagents both off, or nothing selected at all), confirm explicitly before proceeding rather than silently running a stripped-down flow.

   Record all three toggles — they gate steps 6, 8, and 9.

4. **Choose workspace mode** — ask (`AskUserQuestion`): create an isolated **worktree** (recommended for parallel development) or just a **branch** in the current directory.

   **Branch naming** (both modes):
   - Short kebab-case slug from the issue title, including the issue number.
   - Prefix by nature: `feat/` (feature), `fix/` (bug), `build/` (CI/build), `test/` (tests), `chore/` (maintenance, refactor, docs). If unsure, ask.
   - Format: `<prefix>/<issue-number>-<slug>`.

   **If worktree:** use `superpowers:using-git-worktrees` to create the workspace branching off `main` (always from `main`, regardless of current branch).

   **If branch only:** `git checkout -b <branch-name> main`.

5. **Brainstorm the approach** — invoke `superpowers:brainstorming` to reach alignment on:
   - What the issue requires, relevant codebase areas and existing patterns, options and trade-offs.
   - If the issue links files in `docs/specs/` or `docs/plans/`, read them first.

   Brainstorming ALWAYS runs — it produces the shared understanding the next steps build on.

6. **Architect review** *(only if enabled in step 3)* — invoke the `architect` skill to formalize the brainstormed approach into a reviewed, written spec.

   **Tell the architect to run in spec-only mode:** produce and get user approval on the spec, then return control here. It must NOT invoke `writing-plans` or enter plan mode — this skill drives planning in step 7.

   Pass the brainstorming outcome as context so the architect refines rather than restarts the discussion.

   **If disabled:** skip — the brainstorming outcome from step 5 feeds directly into step 7.

7. **Write the plan** — invoke `superpowers:writing-plans` to turn the spec (or, if the architect was skipped, the brainstormed approach) into a step-by-step implementation plan.

8. **Implement:**
   - **Subagent-driven development ON** *(default)* → invoke `superpowers:subagent-driven-development` to execute the plan in this session via subagents.
   - **Subagent-driven development OFF** → implement the plan directly in this session yourself, following `superpowers:test-driven-development` (tests first). Do NOT use `superpowers:executing-plans` here — that skill is for handing the plan to a separate session; only reach for it if the user explicitly wants a separate reviewed execution session.

9. **Finish up** *(only if enabled in step 3)* — invoke the `close-task` skill to wrap up: run the checks gate, push the branch, and open the MR.

   Pass the issue number and branch already known from steps 1–4 so `close-task` skips its own re-identification. Do NOT re-derive them. **If the architect produced a spec in step 6, also pass its path** so `verify-work` runs against it even when the issue body doesn't link the spec (`close-task` otherwise only verifies when the issue references a spec).

   **The finish-up toggle authorizes pushing and opening the MR for a PASSING result** — on the green path, do not add a separate "shall I push?" prompt. It does NOT pre-authorize anything else: if the checks gate or `verify-work` fails, `close-task` is a **hard stop** — it shows the output and does not push. The user fixes and re-runs; there is no "push anyway" path, and the up-front toggle never overrides a red gate.

   **Loop back to next work:** after the MR is up, `close-task` suggests the user's other open issues. If the user picks one, start it by invoking this skill (`implement-task`) again for that issue.

   **If disabled:** stop after implementation. Tell the user the branch is ready and that they can run `/close-task` when they want to push and open the MR.

## Quick Reference

| Step | Skill / tool | Conditional? |
|------|--------------|--------------|
| Select + assign issue | `glab` | always |
| Execution mode | `AskUserQuestion` | always |
| Workspace | `superpowers:using-git-worktrees` / `git` | always |
| Brainstorm | `superpowers:brainstorming` | always |
| Architect (spec-only) | `architect` skill | if enabled |
| Plan | `superpowers:writing-plans` | always |
| Implement | `superpowers:subagent-driven-development` (ON) / `superpowers:test-driven-development` direct (OFF) | mode-dependent |
| Finish up (push + MR) | `close-task` skill | if enabled |

## Common Mistakes

- **Skipping the execution-mode question** — always ask it up front (step 3). Do not assume defaults silently.
- **Letting the architect run to plan mode** — when enabled, the architect runs spec-only; this skill owns `writing-plans`.
- **Double-planning** — `writing-plans` runs exactly once (step 7), not inside the architect.
- **Skipping brainstorming** — it always runs, even when the architect is enabled.
- **Adding a mid-flow push prompt** — the finish-up toggle authorizes the push on a *passing* result; don't ask "shall I push?" again on the green path. A failing checks gate or verify-work is a hard stop — `close-task` shows the output and does not push. There is no "push anyway" path.
- **Re-deriving issue/branch in finish-up** — pass what steps 1–4 already know to `close-task`.
