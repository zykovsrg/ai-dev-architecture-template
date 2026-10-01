# Module: learning

Id: learning
Required: no
Switchable: yes
Depends: core
Uses if present: planning
Rules: ai/rules/learning.md
Keywords: —

## Purpose

Review agent behaviour for a finished task or session, save evidence-backed
findings, and track workflow friction over time.

## Installs

- modules/learning/rules.md -> ai/rules/learning.md
- modules/learning/skills/hub-session-review/ -> ai/skills/hub-session-review/
- modules/learning/data/ai/workflow-observations.md -> ai/workflow-observations.md
- modules/learning/scripts/workflow_friction.py -> scripts/workflow_friction.py
- modules/learning/scripts/check-session-review.py -> scripts/check-session-review.py
- modules/learning/scripts/review_proposals.py -> scripts/review_proposals.py
- modules/learning/scripts/check-workflow-memory.sh -> scripts/check-workflow-memory.sh

## Repository only

- —

## Reads

- session review records and workflow observations

## Writes

- workflow observations

## Subscribes

- before-task-close: follow ai/rules/learning.md § before-task-close
