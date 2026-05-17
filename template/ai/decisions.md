# Decisions

Важные активные архитектурные, продуктовые, workflow-решения и решения по модели данных.

Не используй этот файл для мелких багфиксов, косметических правок или обычной истории изменений.

## Шаблон

### YYYY-MM-DD — Название решения

Status: active / superseded / resolved

Decision:

Why:

Impact:

## Текущие решения

### 2026-05-17 — Plan files are source of truth for plan-driven progress

Status: active

Decision:

For Superpowers or other plan-driven workflows, `docs/superpowers/plans/<plan>.md` is the source of truth for execution progress. Agents must update plan checkboxes after each completed plan task, add short `Note:` entries for local judgment calls, and use `Plan Task <N>: <short action>` commit messages for plan-driven commits.

Why:

Internal TodoWrite state is session-local and disappears when switching agents or chats. Keeping progress in the plan file and using a simple commit convention makes handoff verifiable without extra tools.

Impact:

Ordinary non-plan-driven tasks are unchanged. `ai/decisions.md` remains for durable decisions, `ai/changelog.md` remains for notable summaries, and plan notes are used only for local decisions inside a specific plan.
