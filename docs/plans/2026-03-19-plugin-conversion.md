# varno-devflow Plugin Conversion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the existing agents/skills repo into a proper Claude Code plugin by adding the manifest layer.

**Architecture:** Add `.claude-plugin/` directory with plugin.json and marketplace.json, add `hooks/` directory with SessionStart hook and reference card. Update README with plugin install instructions. No changes to existing skills or agents.

**Tech Stack:** Claude Code plugin format (JSON manifests, markdown, shell hooks)

**Spec:** `docs/specs/2026-03-19-plugin-conversion-design.md`

---

### Task 1: Add plugin manifest

**Files:**
- Create: `.claude-plugin/plugin.json`
- Create: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Create `.claude-plugin/plugin.json`**

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

- [ ] **Step 2: Create `.claude-plugin/marketplace.json`**

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

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/plugin.json .claude-plugin/marketplace.json
git commit -m "Add Claude plugin manifest for varno-devflow"
```

---

### Task 2: Add SessionStart hook

**Files:**
- Create: `hooks/hooks.json`
- Create: `hooks/session-context.md`

- [ ] **Step 1: Create `hooks/hooks.json`**

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

- [ ] **Step 2: Create `hooks/session-context.md`**

```markdown
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
```

- [ ] **Step 3: Commit**

```bash
git add hooks/hooks.json hooks/session-context.md
git commit -m "Add SessionStart hook with skills/agents reference card"
```

---

### Task 3: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update README title and description**

Replace line 1:
- Old: `# Claude Code Agents & Skills Library`
- New: `# varno-devflow`

Replace line 3:
- Old: `Reusable, project-agnostic agents and skills for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). Drop them into any project's ~/.claude/ directory to get a consistent set of workflows.`
- New: `A Claude Code plugin for parallel workspace development workflows. Includes an architect agent, task tracking via beads (bd), and multi-worktree support.`

- [ ] **Step 2: Update README Setup section**

Replace the existing Setup section (lines 7-14) with:

    ## Setup

    ### As a Claude Plugin (recommended)

    Install directly from the repo:

        claude plugin install ~/Documents/myclaude

    ### Manual (symlinks)

        ln -sf ~/Documents/myclaude/agents ~/.claude/agents
        ln -sf ~/Documents/myclaude/skills ~/.claude/skills

- [ ] **Step 3: Commit**

```bash
git add README.md
git commit -m "Update README with plugin installation instructions"
```

---

### Task 4: Verify installation

- [ ] **Step 1: Test plugin install**

```bash
claude plugin install ~/Documents/myclaude
```

Verify: no errors, plugin appears in installed list.

- [ ] **Step 2: Verify skills are available**

Start a new Claude Code session and check that `/architect`, `/start-task`, `/close-task`, `/merge-workspace`, `/visual-qa` are all available as slash commands.

- [ ] **Step 3: Verify SessionStart hook fires**

Check that the reference card appears at conversation start.

- [ ] **Step 4: Verify symlink method still works**

Remove the plugin install, set up symlinks, and confirm skills still load.

- [ ] **Step 5: If any issues, fix and re-commit**
