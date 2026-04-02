# varno-devflow

## Available Skills
| Command | Description |
|---------|-------------|
| `/architect` | Start an architectural discussion about a feature |
| `/start-task` | List GitLab issues (glab), pick one, create branch, brainstorm |
| `/close-task` | Wrap up work, push, create MR (issue closes on merge) |
| `/merge-workspace` | Merge a worktree branch into main |
| `/visual-qa` | Visual QA with Playwright screenshots |

## Available Agents
| Agent | Model | Use for |
|-------|-------|---------|
| `architect` | opus | Architecture decisions, feature design, spec writing |
| `frontend-engineer` | sonnet | Frontend implementation from specs with testing |

## Task Tracking
This plugin uses GitLab issues via `glab` CLI for task tracking. If `glab` is not installed, skills will prompt you to install it.
