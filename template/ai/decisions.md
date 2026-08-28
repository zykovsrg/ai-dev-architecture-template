# Decisions

Важные активные архитектурные, продуктовые, workflow-решения и решения по модели данных конкретного проекта.

Не используй этот файл для мелких багфиксов, косметических правок, обычной истории изменений или решений самого шаблона AI-архитектуры.

## Шаблон

### YYYY-MM-DD — Название решения

Status: active / superseded / resolved

Decision:

Why:

Impact:

## Текущие решения

No project decisions yet.

### 2026-08-28 — Archiproject groups

Status: active

Decision: Overview grouping uses only a group record's `primary_archiproject`.

Why: Groups organize projects without inventing numeric targets or
contributions.

Impact: Group-linked cards use `archiproject_contribution: none`; goal-linked
cards retain numeric contribution.
