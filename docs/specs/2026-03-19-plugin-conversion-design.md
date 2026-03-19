# Design: Convert varno-devflow to Claude Plugin

## Overview

Convert the existing agents/skills repo into a proper Claude Code plugin by adding the plugin manifest layer. The repo's `skills/` and `agents/` directories already match the plugin format — this is an additive change with no modifications to existing files.

## Requirements

- Plugin name: `varno-devflow`
- Distribution: personal install now, publishable to marketplace later
- Beads (`bd`) integration: required by start-task/close-task, prompt to install if missing
- SessionStart hook: lightweight reference card listing available skills/agents
- No changes to existing skill or agent files

## New Files

### `.claude-plugin/plugin.json`

Core plugin metadata. Required for Claude to recognize the repo as a plugin.

```json
{
  "name": "varno-devflow",
  "description": "Parallel workspace development workflows with architect, task tracking (beads), and multi-worktree support",
  "version": "0.1.0",
  "author": {
    "name": "CucoStudio"
  },
  "repository": "https://github.com/cucostudio/varno-devflow",
  "license": "MIT"
}
```

### `.claude-plugin/marketplace.json`

Marketplace registration metadata for future publishing.

```json
{
  "name": "varno-devflow",
  "description": "Parallel workspace development workflows with architect, task tracking (beads), and multi-worktree support",
  "owner": {
    "name": "CucoStudio"
  },
  "plugins": [
    {
      "name": "varno-devflow",
      "description": "Parallel workspace development workflows",
      "version": "0.1.0",
      "source": "./"
    }
  ]
}
```

### `hooks/hooks.json`

SessionStart hook that injects a reference card into every conversation.

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "cat \"${CLAUDE_PLUGIN_ROOT}/hooks/session-context.md\"",
            "async": false
          }
        ]
      }
    ]
  }
}
```

### `hooks/session-context.md`

Lightweight reference card listing available skills, agents, and task tracking info.

## Updated Files

### `README.md`

Add plugin installation instructions alongside existing symlink method.

## File Tree After Conversion

```
varno-devflow/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── hooks/
│   ├── hooks.json
│   └── session-context.md
├── agents/
│   ├── architect.md
│   └── frontend-engineer.md
├── skills/
│   ├── architect/SKILL.md
│   ├── start-task/SKILL.md
│   ├── close-task/SKILL.md
│   ├── merge-workspace/SKILL.md
│   └── visual-qa/SKILL.md
├── docs/specs/
├── README.md
└── LICENSE
```

## Acceptance Criteria

- `claude plugin install /path/to/varno-devflow` works
- All 5 skills appear as available slash commands
- Both agents are available for dispatch
- SessionStart hook fires and shows the reference card
- Existing symlink installation still works as fallback
