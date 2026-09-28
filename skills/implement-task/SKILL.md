---
name: implement-task
description: Use when starting work on a GitLab issue and taking it all the way through design to implementation. Triggers include picking up a tracked issue, "implement issue #N", "let's build the next task", or beginning feature work that needs design and a plan before coding.
user-invocable: true
argument-hint: [issue number or title substring]
---

Take a GitLab issue from selection through design, planning, and implementation.

## Overview

This skill orchestrates a full task pipeline: pick an issue, brainstorm the approach, optionally formalize it with the architect (spec), turn the spec/approach into a plan, then implement. Two stages are optional and chosen up front:

- **Architect review** — the `architect` skill produces and gets approval on a written spec.
- **Subagent-driven development** — the plan is executed via `superpowers:subagent-driven-development`.

By default both are ON. The user can turn either off at the start.

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

   > "Implement with defaults (architect review + subagent-driven development), or change one of those options?"

   - **Defaults** → architect review ON, subagent-driven development ON.
   - **Change options** → ask a follow-up `AskUserQuestion` (multi-select): "Which stages should be enabled?" with options **Architect review** and **Subagent-driven development**. Enabled = selected; unselected = OFF.
     - If the user selects **neither**, confirm explicitly before proceeding ("This runs a plain brainstorm → plan → direct implementation with no architect spec and no subagents — is that what you want?"). Don't silently proceed with both off.

   Record both toggles — they gate steps 6 and 8.

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

## Common Mistakes

- **Skipping the execution-mode question** — always ask it up front (step 3). Do not assume defaults silently.
- **Letting the architect run to plan mode** — when enabled, the architect runs spec-only; this skill owns `writing-plans`.
- **Double-planning** — `writing-plans` runs exactly once (step 7), not inside the architect.
- **Skipping brainstorming** — it always runs, even when the architect is enabled.
