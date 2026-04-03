# debugging-with-logs Skill Design

## Purpose
A language-agnostic technique for using strategic, temporary logging to diagnose bugs or understand code behavior. All added logs are marker-tagged for guaranteed cleanup.

## Location
`varno-devflow/skills/debugging-with-logs/SKILL.md`

## Relationship to Other Skills
- **REQUIRED BACKGROUND:** `superpowers:systematic-debugging`
- Can be used independently (comprehension) or within systematic-debugging Phase 1
- This skill is part of varno-devflow, not superpowers

## Core Flow

### Three Phases

1. **Assess** — Survey existing logging in the problem area. What's already observable? What gaps exist? Decide whether additional logging is actually needed.

2. **Instrument** — Add targeted logs with a consistent marker (`[DBG-TRACE]`). Each log captures: location, context (variable state), and direction (entry/exit). Log at boundaries first, then narrow inward.

3. **Cleanup** — Grep for marker, remove all tagged logs, verify zero remaining matches. Hard gate: cannot claim complete until verified clean.

## Marker Convention
- All added logs include `[DBG-TRACE]` prefix
- Language-agnostic: adapts to whatever logging mechanism the project uses
- Marker makes debug output filterable and cleanup grep-able

## Key Principles
- Evaluate before adding — read existing logging first
- Boundaries first — start at component/function boundaries, then narrow
- State, not just presence — log variable values, not just "got here"
- Mandatory cleanup verification — grep must return zero results

## Scope Boundaries
- NOT a replacement for systematic-debugging
- NOT a guide for production logging strategy
- NOT about log levels, infrastructure, or observability architecture

## Trigger Conditions
- Independently: understanding code flow, verifying assumptions before refactor
- Within systematic-debugging: Phase 1 when more observability is needed
- When existing logging is insufficient for diagnosis

## Cleanup Enforcement
- Mandatory `grep -r "DBG-TRACE"` verification before completion
- Blocks any "done" claim until zero matches confirmed
