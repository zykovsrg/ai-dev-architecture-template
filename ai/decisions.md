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

### 2026-08-28 — Archiproject groups

Status: active

Decision: Overview grouping uses only a group record's `primary_archiproject`.

Why: Groups organize projects without inventing numeric targets or contributions.

Impact: Group-linked cards use `archiproject_contribution: none`; goal-linked cards retain numeric contribution.

### 2026-08-28 — Короткие ветки для общих файлов

Status: active

Decision: Перед работой и review общих часто меняемых файлов ветка синхронизируется с `main`; проверенные ветки сливаются сразу. Параллельная работа в одном файле допускается только после разделения файла или по очереди.

Why: Это снижает ручные merge-конфликты и риск потерять изменения.

Impact: Крупный Kanban-генератор будет вынесен в отдельную future-задачу на модульное разделение.

### 2026-08-28 — Provenance и inbox локальных знаний

Status: active

Decision: Каждый record хранит `origin` и `valid_from`; слабые наблюдения живут только в project-local `knowledge/inbox/` до явного review.

Why: Это отделяет прямые факты от вывода агента и не превращает слабые сигналы в долговременное знание автоматически.

Impact: Capture не выбирает origin по умолчанию; review отдельно показывает inferred и требует точного подтверждения для promotion, retention или удаления inbox-записей.

### 2026-08-24 — Unified assistant: canonical data and safe human control

Status: active

Decision: The hub and each project's `ai/` records remain the canonical
source for archiprojects, projects, tasks, subtasks, deadlines, and waiting.
Obsidian is a generated local human-facing projection, not a second task
database. One project has at most one `primary_archiproject`; only
`archiproject_contribution` affects its progress, while
`related_archiprojects` never double-count. A zero contribution is valid.
Waiting belongs to a task or subtask; a project is shown as Waiting only when
it has no other actionable work.

The first Obsidian surface has two generated views. `Tasks-Kanban.md` has one
card per canonical task, with task-status columns Ideas, Ready, Active,
Waiting, Blocked, Review, Paused, and Done. Each card names its parent project.
`Projects-Overview.md` is a table with one row per project and derived
current-task, ready, waiting, and due-date fields; it is not a Kanban. Both
views share one manifest. A manual edit to either view blocks regeneration with
`proposal pending`. Future `promoted`, `done`, and `dropped` entries do not
create open task cards. Knowledge uses a mixed PARA-style structure:
project knowledge stays with its project; shared knowledge stays once in the
common base, including shared meetings. Inbox is a fallback for ambiguous
captures, not a mandatory stop.

Agents may analyse and propose. Every write of a task, deadline, note,
Obsidian file, Calendar event, or migration requires a fresh explicit user
confirmation. Calendar integration is deferred: use a selected test calendar,
preview first, separate write confirmation, and no deletion. A separate
session-audit task starts every three days and may automatically refresh only
the metadata inventory. The user's exact session IDs authorize reading only
those transcripts and immediately writing safe audit results to the journal.
Findings may propose changes, but never automatically change tasks, rules,
settings, or architecture.

Why: The user needs fast retrieval and planning across many projects without
losing manual control, data ownership, or the hub's narrow routing boundary.

Impact: Continue in ordered phases: read-only vault inventory and Obsidian
projection design; confirmed projection implementation; workflow commands and
reviews; then a separately confirmed Apple Calendar MCP pilot. Never treat old
checkboxes or Kanban cards as canonical tasks without classification.

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
