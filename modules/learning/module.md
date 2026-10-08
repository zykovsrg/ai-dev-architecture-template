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
- modules/learning/skills/hub-session-scan/ -> ai/skills/hub-session-scan/
- modules/learning/scripts/session_collect.py -> scripts/session_collect.py
- modules/learning/scripts/session_rules.py -> scripts/session_rules.py
- modules/learning/scripts/session_scan_model.py -> scripts/session_scan_model.py
- modules/learning/scripts/open_task_check.py -> scripts/open_task_check.py
- modules/learning/data/ai/learning/rules.json -> ai/learning/rules.json
- modules/learning/data/ai/learning/scan-ledger.json -> ai/learning/scan-ledger.json
- modules/learning/data/ai/learned-rules.md -> ai/learned-rules.md
- modules/learning/agents/claude/hub-session-scanner.md -> .claude/agents/hub-session-scanner.md
- modules/learning/agents/claude/hub-learning-consolidator.md -> .claude/agents/hub-learning-consolidator.md

## Repository only

- modules/learning/tests/

## Reads

- session review records and workflow observations
- Claude Code and Codex transcripts of Hub sessions (read-only)

## Writes

- workflow observations
- learning catalog, scan ledger and learned-rules files

## Subscribes

- —
