# varno-devflow

## Available Skills
| Command | Description |
|---------|-------------|
| `/architect` | Start an architectural discussion about a feature |
| `/start-task` | Find a ready task (bd), claim it, create branch, plan |
| `/close-task` | Close a beads task and commit |
| `/merge-workspace` | Merge a worktree branch into main |
| `/visual-qa` | Visual QA with Playwright screenshots |

## Available Agents
| Agent | Model | Use for |
|-------|-------|---------|
| `architect` | opus | Architecture decisions, feature design, spec writing |
| `frontend-engineer` | sonnet | Frontend implementation from specs with testing |

## Task Tracking
This plugin uses beads (`bd`) for task tracking. If `bd` is not installed, skills will prompt you to install it.
