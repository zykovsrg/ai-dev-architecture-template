# Module: learning

Id: learning
Required: no
Switchable: no
Depends: core
Uses if present: —
Rules: ai/rules/learning.md
Keywords: —

## Purpose

Review agent behaviour for a finished task or session, save evidence-backed
findings, and track workflow friction over time.

## Installs

- modules/learning/rules.md -> ai/rules/learning.md
- hub-template/ai/skills/hub-session-review/ -> ai/skills/hub-session-review/
- hub-template/ai/workflow-observations.md -> ai/workflow-observations.md
- scripts/workflow_friction.py -> scripts/workflow_friction.py
- scripts/check-session-review.py -> scripts/check-session-review.py
- scripts/check-workflow-memory.sh -> scripts/check-workflow-memory.sh

## Repository only

- —

## Reads

- session review records and workflow observations

## Writes

- workflow observations

## Subscribes

- —
