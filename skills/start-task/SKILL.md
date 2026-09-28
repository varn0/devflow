---
name: start-task
description: Use when starting work on a GitLab issue — listing issues, picking one, creating a branch/worktree, and beginning implementation. Alias kept for backwards compatibility; the current workflow lives in implement-task.
user-invocable: true
argument-hint: [issue number or title substring]
---

`start-task` is a backwards-compatibility alias for `implement-task`.

**Invoke the `implement-task` skill** (via the Skill tool) and follow it exactly, passing along `$ARGUMENTS`. Do not implement a separate flow here — `implement-task` is the single source of truth for the task pipeline (select issue → brainstorm → optional architect spec → plan → implement).
