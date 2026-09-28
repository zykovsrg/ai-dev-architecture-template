# Decisions

### 2026-09-28 — knowledge, goals, learning выключаемые; скрипты хаба совместимы с Python 3.9

Status: active

Decision: knowledge, goals и learning помечены `Switchable: yes` и
выключаются так же, как obsidian, planning и calendar: `--without <id>` в
обычном обновлении хаба. Выключение убирает только управляемые файлы модуля
(навыки, правила, скрипты); `ai/goals.md`, `ai/goal-log.md`,
`ai/workflow-observations.md` и всё в `projects/` (knowledge, разборы сессий)
остаются. Ни один модуль не указывает их в `Depends:`; planning использует
goals и learning только если они стоят. Скрипты, которые ставятся в хаб,
должны работать на системном Python 3.9 macOS: аннотации вида `X | None`
только с `from __future__ import annotations`.

Why: `read-compact-task-index.py` падал на системном Python 3.9.6 (`python3`
в части сессий) из-за аннотации, появившейся на этапе 6 (исправлено в
1242190). Выключаемость трёх модулей — следующий шаг модульной архитектуры
после этапа 8.

Impact: `tests/test_optional_modules_switch.py` проверяет выключение и
включение каждого модуля и сохранность данных; `tests/test_python39_compat.py`
проверяет все устанавливаемые `.py` на такие аннотации. Таблица модулей — в `docs/update.md`.

### 2026-09-27 — Защиту обновления хаба не обходить

Status: active

Decision: Если `update-installed-hub.sh` останавливается из-за своей защиты
(грязное дерево хаба, конфликт), агент называет причину и спрашивает
пользователя. Флаги обхода (`--allow-dirty` и подобные) агент сам не
добавляет: «да» на обновление не означает «да» на отключение его проверок.

Why: разбор сессии этапа 7 (P1 в
`ai/session-reviews/2026-09-27-split-architecture-stage-7-closure.md`),
принято пользователем 2026-09-27.

Impact: при остановке обновления — вопрос пользователю, а не команда с флагом обхода.

### 2026-09-27 — Все модули в `modules/`, строгие границы

Status: active

Decision: Every module — including core, projects and tasks, the three that
stayed in `hub-template/` through stages 4–7 — now sources its skills,
scripts, and data templates from `modules/<id>/{skills,scripts,data}`.
`hub-template/` is removed; every passport's `## Installs` lines point at
`modules/<id>/…` sources instead. Installed Hub target paths are unchanged
(proved by comparing `install_pairs` target sets before and after this
task). The dependency rule is refined: core, projects and tasks — the
always-installed modules — may reference each other freely, since none of
them can ever be missing; a reference to an optional module (knowledge,
goals, learning, calendar, planning, obsidian) is still allowed only from
itself, a module that lists it in `Depends:`/`Uses if present:`, or through
an event or `ai/modules.md`. `check-module-boundaries.py --strict` now adds
core, projects and tasks to every module's allowed set and is a failing test
in `architecture-test.sh` (boundary warnings 27 → 0).

Two new events: `before-task-close`, fired by `hub-task-finish` after Done
criteria pass and before task memory is cleared (learning subscribes with
the session review; knowledge subscribes with an optional, never
auto-started, knowledge review; no subscriber → closure proceeds as before);
and `after-project-create`, fired by `hub-project-create` after the
confirmed scaffold is written (knowledge subscribes and creates the empty
`knowledge/` scaffold on the same confirmation screen).

`hub-project-router`, `CLAUDE.md`, and `AGENTS.md` no longer name an
optional skill by name. They resolve the planning and learning skill by role
through `ai/modules.md`'s `## Skills` section; if the role has no listed
module, they say so instead of guessing a skill name.

Amends: the 2026-08-15 skill-naming decision and the stage-7 decision
(`ai/decisions.md` 2026-09-27 "Правила модулей живут в `ai/rules/<id>.md`")
— both name `hub-template/CLAUDE.md`, `hub-template/AGENTS.md`, and
`hub-template/ai/architecture.md` as live paths; those paths are now
`modules/core/data/CLAUDE.md`, `modules/core/data/AGENTS.md`, and
`modules/core/data/ai/architecture.md`. The historical decision text itself
is left as written (it described the state at the time); this entry
supersedes only the path mentions for anyone acting on them going forward.

Why: Stage 8 of
`docs/superpowers/specs/2026-09-26-modular-architecture-design.md` — the
last three modules were the last exception to "every module lives in
`modules/<id>/`", and a warning-only boundary check does not stop new
violations from creeping back in.

Impact: `hub-template/` no longer exists. Every live reference to it in
tooling, tests, and active docs (README.md, docs/concepts.md,
docs/file-roles.md, ai/project-context.md, ai/current-task.md) was updated
to `modules/…`; historical records (changelogs, decisions, old specs and
plans, session reviews, the paused/future task backlog) were left as
written. `check-module-boundaries.py --strict` is now part of
`architecture-test.sh`'s required test run.

### 2026-09-27 — Правила модулей живут в `ai/rules/<id>.md`

Status: active

Decision: Amends 2026-08-15 — a Hub skill may now be named in
`modules/<id>/rules.md` instead of `hub-template/CLAUDE.md`, `AGENTS.md`, or
`hub-template/ai/architecture.md`. Route-then-confirm is defined only in
`hub-project-router`; core no longer restates it. Each module's rules live in
`ai/rules/<id>.md` (installed from `modules/<id>/rules.md`), referenced by a
`Module rules: ai/rules/<id>.md` pointer at the top of every skill belonging
to that module. `hub-template/ai/architecture.md` keeps only cross-module
core: ownership map, module-loading rules, context-loading budget, and the
mode-based write-permission paragraphs of Information Updates.

Why: Stage 7 of `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`
— a project session that installs only some modules should not have to load
planning/knowledge/calendar/learning/goals procedures it never uses.

Impact: `check-consistency.sh` § "hub skill naming" now searches
`modules/*/rules.md` together with the three core files. `check-module-boundaries.py`
warnings dropped 55 → 27 once core stopped naming other modules' skills and
files in running text. `hub-template/ai/architecture.md` is `Version: 2.0`.

### 2026-09-27 — Nested groups; goals in `ai/goals.md`; cards keep only their group

Status: active

Decision: `ai/archiprojects.md` holds only groups, optionally nested with
`parent:` (depth ≤ 3, no cycles). Goals live in `ai/goals.md` and name a group.
A project card declares only `primary_archiproject: <group-id|none>`; the
project also belongs to every ancestor group. `archiproject_contribution` and
`related_archiprojects` are removed. Migrated 2026-09-27: `hadassah-promo`
(29 projects, goal 32 promo pages) and `hadassah-seo` (8 projects, goal 80 SEO
pages) under `hadassah`.

Why: Stage 6 of `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`.

Impact: supersedes the contribution/related parts of decisions 2026-08-24 and
2026-08-28. Group-wide overview and plans read only member projects.

### 2026-09-27 — Planning and calendar are switchable modules

Status: active

Decision: planning (`modules/planning/`) and calendar (`modules/calendar/`) are
optional modules. Task skills reach planning only through
`before-task-confirmation` (rules in `ai/rules/planning.md`); `hub-calendar`
fires `after-calendar-change` and knows nothing of tasks or planning. Capture
and task overviews live in the tasks skill `hub-task-overview`. The calendar MCP
has no evening-review tool; snapshots have one writer (planning). Switching
calendar also installs or removes `tools/apple-calendar-policy` and the
`hub_calendar` entry in `.mcp.json`; user data stays. Both modules are enabled
in the working Hub.

Why: Stage 5 of `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`.

Impact: a task and its calendar event are still confirmed together; the
calendar change is applied first and a failure writes nothing to the task.

### 2026-09-27 — Obsidian is an optional module, disabled in the working Hub

Status: active

Decision: Obsidian lives in `modules/obsidian/` and is installed only when
selected. Task skills never call it directly; they fire `after-task-write`
through the generated `ai/modules.md`. The working Hub runs without it
(`update-installed-hub.sh --without obsidian`); the selection is stored in
`.local/hub-release/installed.json`. Re-enable with `--with obsidian`.

Why: Stage 4 of the modular architecture; Obsidian is the pilot switchable
module (spec `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`,
section `Stage 4 details`).

Impact: the 2026-08-29 decision `Scoped Obsidian reverse proposals` applies only
while the module is installed. The vault and its boards stay untouched but no
longer refresh. Release files come only from module passports.

### 2026-09-27 — The architecture repository is the only source of Hub runtime files

Status: active

Decision: Every file installed into the Hub (skills, entry files, runtime
scripts) is authored in this repository (`hub-template/`, `scripts/`,
`calendar-policy/`) and reaches the Hub only through
`scripts/update-installed-hub.sh`. After every Hub update,
`python3 scripts/hub_release.py drift --source <repo> --hub <hub>` must exit 0
(no conflicts, no unmanaged files). Tests live in this repository's `tests/`.

Why: by 2026-09-26 planning work had been done directly in the Hub; 10 skills,
4 scripts and 9 tests diverged, and `calendar_task_sync.py` existed only in the
Hub, so a reinstall would have lost it.

Impact: a change made in the Hub first must be brought back here before the
next update; `drift` shows it as a conflict or an unmanaged file. Target module
layout: `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`.

### 2026-09-10 — Refactor scope and approval boundaries

Status: active

Decision: Centralize generic project rules in the hub; preserve task/calendar
learning and goal workflows. Add session review at closure and on request;
apply improvements only after user confirmation. Codex scheduled automation
is not the requested self-learning mechanism. Use Astra for design/plans and
Terra or Luna for economical implementation/review when actually available.

Impact: Application testing is out of audit scope. User declined extra
regression checks after deployment; this does not establish that checks passed.
See `ai/refactor-handoff-2026-09-10.md` for evidence and remaining concerns.

Важные активные архитектурные, продуктовые, workflow-решения и решения по модели данных конкретного проекта.

Не используй этот файл для мелких багфиксов, косметических правок, обычной истории изменений или решений самого шаблона AI-архитектуры.

## Шаблон

### YYYY-MM-DD — Название решения

Status: active / superseded / resolved

Decision:

Why:

Impact:

## Текущие решения

### 2026-09-10 — Единый формат дневного планирования

`day-plan` показывает ровно пять разделов: текущий календарь, подтверждённые
конфликты, задачи проектов вне календаря, просроченные задачи и итоговый
предлагаемый календарь. Одна задача не повторяется между разделами задач;
продолжительность предложенного блока помечается как указанная или оценочная.
Это правило живёт в `hub-workflows` и архитектуре хаба.

Календарные разделы выводятся маркированным списком: одна строка на событие,
сначала время, затем название. Абзацы с несколькими событиями не допускаются.
Заголовок уже существующего события копируется дословно, а для нового блока
используется точное название задачи из канонической записи.

Ясные запросы на планирование текущего дня сразу запускают `day-plan` и не
могут получить свободный предварительный ответ вместо пяти разделов плана.

### 2026-09-05 — Закрытие задачи автоматически чистит память и сохраняет результат

Status: active

Decision: Проверка закрытия задачи и последующие действия — один шаг. Если
`task-finish` не нашёл блокирующей причины, он сразу обновляет `ai/changelog.md`,
`ai/decisions.md`, `ai/future-tasks.md`, очищает `ai/current-task.md` и сохраняет
результат коммитом и пушем. Отдельного подтверждения перед очисткой нет.

Why: Второе подтверждение ничего не проверяло дополнительно и оставляло задачи
незакрытыми, а изменения — несохранёнными.

Impact: Отчёт о закрытии обязан перечислять все автоматические записи и коммит.
То же правило действует в хабовом `hub-task-finish`. Единственное исключение —
задача с расписанием: её закрытие меняет ещё и календарь, поэтому там остаётся
один общий экран подтверждения памяти и события.

### 2026-09-03 — Задача с расписанием и её событие подтверждаются вместе

Status: active

Decision: Правка памяти задачи и полное превью события Apple Calendar
показываются одним экраном и подтверждаются одним ответом, покрывающим ровно
показанную пару. Расписание задаётся полем
`Запланировано: <YYYY-MM-DD> <HH:MM>-<HH:MM>`, а одиночный `Due:` даёт событие
на весь день. Если превью построить нельзя, не применяется ни одна из частей.

Why: Задача со сроком и её событие — одно изменение, разнесённое по двум
хранилищам. Два отдельных подтверждения не делали его безопаснее, зато
позволяли остановиться посередине и оставить календарь расходящимся с памятью
задач.

Impact: `hub-task-intake`, `hub-task-switch` и `hub-task-finish` ведут события
задач. Правило «одно подтверждение на изменение» в `hub-calendar` сохраняется
для всего остального: превью остаётся полным, а непоказанное или изменённое
событие требует своего подтверждения.

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

Status: superseded 2026-09-27 — the installer
`scripts/install-legacy-hub-obsidian-bridge.sh` was removed as dead code
(TASK-ai-dev-architecture-20260926-001, commit 551c4e4): none of the 71
registered projects carries the `## Hub Obsidian Bridge` block and none uses the
legacy project-local layout. Restore from git only if a legacy direct project
reappears.

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
