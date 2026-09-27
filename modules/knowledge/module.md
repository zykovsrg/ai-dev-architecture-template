# Module: knowledge

Id: knowledge
Required: no
Switchable: no
Depends: core, projects
Uses if present: —
Rules: ai/rules/knowledge.md
Keywords: —

## Purpose

Optional per-project knowledge scaffold: enable, capture and review knowledge
records, and turn transcript info into scoped update proposals.

## Installs

- modules/knowledge/rules.md -> ai/rules/knowledge.md
- modules/knowledge/skills/hub-knowledge-enable/ -> ai/skills/hub-knowledge-enable/
- modules/knowledge/skills/hub-knowledge-capture/ -> ai/skills/hub-knowledge-capture/
- modules/knowledge/skills/hub-knowledge-review/ -> ai/skills/hub-knowledge-review/
- modules/knowledge/skills/hub-info-update/ -> ai/skills/hub-info-update/

## Repository only

- —

## Reads

- project knowledge records

## Writes

- project knowledge records

## Subscribes

- before-task-close: follow ai/rules/knowledge.md § before-task-close
- after-project-create: follow ai/rules/knowledge.md § after-project-create
