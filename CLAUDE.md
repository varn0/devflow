# varno-devflow

Claude Code plugin for parallel workspace development using git worktrees, architecture-first design, and GitLab issue tracking via `glab`.

## Project structure

```
.claude-plugin/   Plugin manifest (plugin.json, marketplace.json)
hooks/            SessionStart hook that injects reference card
agents/           architect.md (Opus), frontend-engineer.md (Sonnet)
skills/           /architect, /start-task, /close-task, /merge-workspace, /visual-qa
docs/             Specs and implementation plans
```

## Key concepts

- **Three-workspace pattern**: Two feature worktrees build in parallel; main handles integration and merging.
- **Architecture-first**: The architect agent enforces a hard gate — no implementation until design is reviewed and approved.
- **Discover, don't hardcode**: Skills detect project structure (test frameworks, worktrees, task files) at runtime.
- **Regular merge, not squash**: Preserves commit SHAs so other worktrees can rebase cleanly.

## Development guidelines

- Each agent/skill file must be self-contained — no dependency on project-specific CLAUDE.md.
- Skills use `glab` CLI for GitLab issue tracking; always check `glab` is available before invoking.
- Keep tasks small for simple merges and frequent integration.
- Specs go in `docs/specs/`, plans in `docs/plans/`, prefixed with date (YYYY-MM-DD).
