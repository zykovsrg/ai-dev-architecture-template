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

### 2026-08-29 — The Calendar bridge owns its own macOS permission

Status: active

Decision: The EventKit bridge ships as a signed application bundle with its own
`NSCalendarsFullAccessUsageDescription`, and re-spawns itself once with the
disclaim attribute so macOS treats the bundle, not the MCP client, as the
process responsible for Calendar access. Clients run the bundle executable
directly; they never run a bare Swift script.

Why: macOS attributes a Calendar decision to the responsible application. A
bridge spawned by a client inherits that client's identity, and a client whose
Info.plist lacks the usage description is refused silently, with no prompt and
no recorded denial. The Calendars pane cannot be filled in by hand, so there is
no recovery from the client side.

Impact: Calendar access is granted once, to `com.personal-ai-hub.calendar-bridge`,
and works from any MCP client. Rebuilding changes the signature and requires
running `scripts/grant-calendar-access.sh` again. Between a rebuild and that
run, `calendar_status` reports `not_determined` even though a real operation
would succeed: the stored decision is re-associated with the new signature by
the first actual access request, not by reading the status. The disclaim symbol is private
API resolved at run time; if it disappears the bridge keeps working and falls
back to asking on behalf of the client.

### 2026-08-29 — Calendar writes are never implicit

Status: active

Decision: Every create, update and delete goes through a preview grant that is
single-use, expiring, bound to the exact request payload and to a fingerprint of
the event as it currently stands. An event whose end is at or before now in the
calendar timezone can be neither deleted nor moved. Reads require explicit
calendar IDs; the allowlist has no default and no fallback to "all calendars".

Why: A calendar change is hard to undo and easy to trigger by accident or by
injected event content. Fail-closed defaults keep an unconfigured or confused
agent harmless.

Impact: One confirmation authorizes exactly one change. A stale preview, an
edited payload, or an event that changed underneath is refused rather than
applied.

### 2026-08-29 — Scoped Obsidian reverse proposals

Status: active

Decision: Format-4 Obsidian uses one Projects Overview table and one board per
project. Reverse scan and apply require a confirmed project ID and may read only
that project board and its canonical task files. The central vault is owned by
ai-dev-architecture; the watcher scans project IDs one at a time and leaves one
applicable proposal.

Why: One shared vault must not weaken project-memory isolation.

Impact: Project agents derive the central vault from the hub root, never ask
for a per-project path, and preserve the separate proposal confirmation gate.

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
### 2026-08-29 — Legacy direct-project Obsidian bridge

Status: active

Decision: A registered legacy project opened directly under the personal hub
may discover the central Obsidian vault only after its hub layout, registry
mapping, and scope membership are validated. It uses the existing scoped
reverse-sync script with its own project ID. A scan creates a proposal only;
canonical task records still require explicit proposal-hash confirmation.

Why: Directly opened 7.3 projects previously used standalone instructions and
asked for a vault path despite a valid central board.

Impact: The migration installer updates only registered version-7.3 direct
children with safe paired entry files, rejects traversal, symlinks, malformed
or duplicate bridge blocks, and rolls back a failed paired replacement. A
divergent legacy entry pair may receive an additive bridge only with explicit
approval and without replacing its existing rules.

### 2026-09-01 — Calendar title rule and its tests move together

Status: active

Decision: Правило формата заголовка события `категория/проект/задача`
(строчными, ровно три непустые части, без пробелов вокруг `/`) живёт в
`calendar-policy/src/hub_calendar_policy/models.py`. Любое изменение этого
правила обязано в том же шаге обновить фикстуры канонических тестов
`calendar-policy/tests/`.

Why: Правило ввели только в зеркале `tools/apple-calendar-policy/` вместе с
`tests/test_title_validation.py`, а канонические тесты не тронули. Пока
источники расходились, это не было видно. При переносе правки в канон
`apple-calendar-policy-test.sh` дал 7 failed + 7 errors — фикстуры
использовали заголовки вида `"Review"`, `"New"`, `"Changed"`, `"Renamed"`.

Impact: Фикстуры приведены к правилу (`работа/проект/ревью` и т.п.), набор
снова зелёный (84 passed). Правку calendar-policy делать только в
каноническом `calendar-policy/` и раскатывать через
`scripts/sync-calendar-policy.sh`; правка прямо в `tools/` создаёт скрытое
расхождение и переживает ровно до следующего синка.

### 2026-08-31 — Past events may be updated and deleted

Status: active

Decision: В hub-calendar разрешено менять и удалять прошедшие события.
Из `calendar-policy/src/hub_calendar_policy/policy.py` убраны
`PAST_EVENT_DELETE_DENIED`, `PAST_EVENT_MUTATION_DENIED` и `_is_past`;
формулировка переписана в `docs/superpowers/specs/2026-08-29-apple-calendar-mcp-design.md`
и в обоих `architecture.md` (хаба и `hub-template/`). Остальные защиты не
менялись: allowlist календарей, запрет записи в read-only календарь,
одноразовое превью и отдельное подтверждение на каждую операцию.

Why: Это осознанное решение пользователя от 2026-08-31, а не регрессия и
не чужая случайная правка.

Impact: Не восстанавливать эту защиту. 2026-09-01 правка полтора дня
пролежала незакоммиченной, следа в git-истории не было, и агент принял её
за молчаливое снятие защиты: восстановил правило, а затем откатил
восстановление — примерно час работы впустую. Правило на будущее: если
встретилось снятое правило, сначала спросить пользователя, его ли это
решение, и только потом что-то менять. Незакоммиченная правка в правилах
сама по себе не улика.
