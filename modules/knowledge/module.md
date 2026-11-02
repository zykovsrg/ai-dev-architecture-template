# Модуль: knowledge

Id: knowledge
Required: no
Switchable: yes
Depends: core, projects
Uses if present: —
Rules: ai/rules/knowledge.md
Keywords: —

## Purpose

Необязательная структура знаний проекта: включать, сохранять и проверять записи знаний,
превращать сведения из расшифровок в предложения обновлений в разрешённых пределах.

## Installs

- modules/knowledge/rules.md -> ai/rules/knowledge.md
- modules/knowledge/data/ai/knowledge/ -> ai/knowledge/
- modules/knowledge/skills/hub-knowledge-enable/ -> ai/skills/hub-knowledge-enable/
- modules/knowledge/skills/hub-knowledge-capture/ -> ai/skills/hub-knowledge-capture/
- modules/knowledge/skills/hub-knowledge-review/ -> ai/skills/hub-knowledge-review/
- modules/knowledge/skills/hub-info-update/ -> ai/skills/hub-info-update/

## Repository only

- —

## Reads

- записи знаний проекта и явно опубликованные общие справочные материалы Хаба

## Writes

- записи знаний проекта

## Subscribes

- before-task-close: следовать ai/rules/knowledge.md § before-task-close
- after-project-create: следовать ai/rules/knowledge.md § after-project-create
