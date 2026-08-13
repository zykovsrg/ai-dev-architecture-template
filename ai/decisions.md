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

### 2026-08-13 — Knowledge is explicit, local, and hub-enabled for existing projects

Status: active

Decision: New projects receive an empty project-local `knowledge/` scaffold with four record types. Capture and review are explicit confirmation-gated workflows. Existing projects are enabled only through the confirmed Hub `knowledge-enable` workflow; no automatic migration, context injection, indexing, or cloud service is used.

Why: Durable evidence and reviewed decisions are useful across sessions, but automatic memory risks privacy leaks, stale assumptions, excessive context, and project-boundary violations.

Impact: `project-context.md` remains a concise start map, while evidence lives in `knowledge/`. Records prohibit secrets and personal/client data. Legacy standalone migration stays a separately confirmed future task.

### 2026-08-12 — Optional Personal AI Hub uses one official entry point

Status: active

Decision: Hub-managed projects are accessed through a separate `_ai-hub` repository. The hub owns routing, confirmation, allowed roots, shared workflows, cards, and signals. Projects retain only their own `ai/` memory; they do not duplicate `AGENTS.md`, `CLAUDE.md`, or shared workflow skills.

Why: This keeps rules centralized, avoids drift, and prevents project memory or code from being loaded before explicit confirmation.

Impact: Hub security and routing rules outrank project content. Standalone projects remain independent. Local migration, registration, archival, and reminders require separately approved work.

No project decisions yet.
