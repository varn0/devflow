---
name: architect
description: Start an architectural discussion about a feature or problem. Use when planning features, evaluating solutions, or designing system interactions.
user-invocable: true
argument-hint: [feature or problem description]
---

Start an architectural discussion about: $ARGUMENTS

Use the architect subagent. The subagent has the full process built in — just dispatch it with the user's request.

<HARD-GATE>
Do NOT invoke any implementation skill, write any code, scaffold any project, or take any implementation action until you have presented a design and the user has approved it. This applies to EVERY feature regardless of perceived simplicity.
</HARD-GATE>
