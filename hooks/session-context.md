# varno-devflow

## Available Skills
| Command | Description |
|---------|-------------|
| `/architect` | Start an architectural discussion about a feature |
| `/implement-task` | Pick a GitLab issue → brainstorm → optional architect spec → plan → implement |
| `/start-task` | Alias for `/implement-task` (backwards compatibility) |
| `/close-task` | Wrap up work, push, create MR (issue closes on merge) |
| `/merge-workspace` | Merge a worktree branch into main |
| `/visual-qa` | Visual QA with Playwright screenshots |
| `/verify-work` | Verify a feature against its spec's Verification Plan |
| `/security-scan` | Run security scanners, merge + dedupe findings into one report (detect-only) |

## Available Agents
| Agent | Model | Use for |
|-------|-------|---------|
| `architect` | opus | Architecture decisions, feature design, spec writing |

## Task Tracking
This plugin uses GitLab issues via `glab` CLI for task tracking. If `glab` is not installed, skills will prompt you to install it.
