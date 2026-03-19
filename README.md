# varno-devflow

A Claude Code plugin for parallel workspace development workflows. Includes an architect agent, task tracking via beads (bd), and multi-worktree support.

## Setup

### As a Claude Plugin (recommended)

Install directly from the repo:

```bash
claude plugin install ~/Documents/myclaude
```

### Manual (symlinks)

```bash
ln -sf ~/Documents/myclaude/agents ~/.claude/agents
ln -sf ~/Documents/myclaude/skills ~/.claude/skills
```

## Agents

| Agent | Model | Description |
|-------|-------|-------------|
| `architect` | opus | Senior software architect for feature design, architecture decisions, and spec writing. Dialogue-first — explores the problem before proposing solutions. |
| `frontend-engineer` | sonnet | Implements frontend features from specs with comprehensive testing. React/TypeScript focused, but adapts to the project's stack. |

## Skills

| Skill | Command | Description |
|-------|---------|-------------|
| `architect` | `/architect` | Start an architectural discussion about a feature or problem |
| `start-task` | `/start-task` | Rebase, find a task in the project's plan file, create a branch, enter plan mode |
| `close-task` | `/close-task` | Mark a task as done in the plan file and commit |
| `merge-workspace` | `/merge-workspace` | Merge a git worktree branch into main with preview and confirmation |
| `visual-qa` | `/visual-qa` | Visual QA testing with Playwright screenshots |

## Parallel Workspace Workflow

These agents and skills are designed around a three-workspace workflow using git worktrees and iTerm split panes, with three Claude Code sessions running simultaneously:

```
┌─────────────────┬─────────────────┬─────────────────┐
│   Workspace A   │   Workspace B   │      Main       │
│   (feature)     │   (feature)     │  (integration)  │
│                 │                 │                 │
│  Build features │  Build features │  Merge & test   │
│  independently  │  independently  │  Resolve conflicts│
│                 │                 │  Small tasks    │
└─────────────────┴─────────────────┴─────────────────┘
```

### How it works

1. **Task triage** — Use `/architect` to evaluate a task. If it's large, produce a spec and merge it to main for later. If it's small, start implementation immediately.
2. **Start work** — On workspace A or B, run `/start-task`. This rebases on main (picking up the latest integrated code) and creates a task branch.
3. **Build in parallel** — Both workspaces implement separate features simultaneously. Tasks are split by feature to avoid overlap.
4. **Merge after each task** — When a workspace finishes, switch to main and run `/merge-workspace` to pull in the changes. Regular merge (not squash) preserves commit SHAs so the other workspace can rebase cleanly.
5. **Repeat** — The other workspace starts its next task, rebases on the updated main, and continues.

### Key rules

- **Small tasks** — Keep features/fixes small so merges stay simple and frequent.
- **Rebase only at task start** — Workspaces rebase on main via `/start-task`, not mid-task.
- **Main handles integration** — The main workspace resolves merge conflicts, runs integration/manual tests, and handles lightweight tasks like backlog grooming.
- **Feature separation** — Assign unrelated features to each workspace to minimize conflicts.

## Design Principles

- **Discover, don't hardcode** — Skills detect project structure (test frameworks, task files, worktrees) rather than assuming paths
- **Methodology over configuration** — The workflows and checklists are the value; project details are discovered at runtime
- **Self-contained** — Each file works standalone without requiring a project-specific CLAUDE.md
