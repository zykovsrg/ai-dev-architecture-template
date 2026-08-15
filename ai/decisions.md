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

### 2026-08-15 — Hub skills must be named in the rules, and checks must be seen failing

Каждая папка `hub-template/ai/skills/*` обязана быть названа в
`hub-template/CLAUDE.md`, `hub-template/AGENTS.md` или
`hub-template/ai/architecture.md`, в обратных кавычках. Это принудительно
проверяет `[hub skill naming]` в `scripts/check-consistency.sh`. Добавление
скилла без упоминания в правилах — красная проверка, а не незамеченное
расхождение слоёв. Совпадение ищется вместе с обратными кавычками: имя,
являющееся началом другого имени, не засчитывается по ошибке.

Новая проверка не считается готовой, пока её не увидели падающей на нарочно
сломанном случае. Аудит 2026-08-15 нашёл три проверки, сообщавшие об успехе,
ничего не сверив; финальное ревью нашло четвёртую — уже внутри правок,
устранявших первые три.

Следствие для версий: любое изменение содержимого `hub-template/ai/architecture.md`
требует поднятия его `Version:`. Установленные хабы узнают об обновлении по
номеру версии, поэтому изменение без поднятия номера не доедет до других машин.

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
