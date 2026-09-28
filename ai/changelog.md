# Changelog

### 2026-09-28 — Выключаемые knowledge, goals, learning; Python 3.9; документация (TASK-ai-dev-architecture-20260928-002)

- 1242190: `read-compact-task-index.py` получил
  `from __future__ import annotations` — на системном Python 3.9.6 он падал
  (аннотация с этапа 6). Новый `tests/test_python39_compat.py` проверяет все
  устанавливаемые `.py` на аннотации `X | None` без `from __future__`
  (увиден падающим до правки).
- 4ec6f3f: knowledge, goals, learning — `Switchable: yes`;
  `tests/test_optional_modules_switch.py` (выключение/включение каждого
  модуля, сохранность `ai/goals.md`, `ai/goal-log.md`,
  `ai/workflow-observations.md`).
- a14edfe: README, `getting-started/help.md`, `docs/*.md` переписаны под
  модули; в `docs/update.md` одна таблица выключаемых модулей, в
  `docs/file-roles.md` раскладка репозитория по модулям. Убраны утверждения,
  которые больше ничем не подтверждены (список — в корневом `CHANGELOG.md`).

### 2026-09-28 — Шаблон хаба игнорирует `.DS_Store` (TASK-ai-dev-architecture-20260928-001)

- `modules/core/data/.gitignore` получил `.DS_Store`; тест
  `test_hub_template_ignores_macos_metadata` (увиден падающим до правки).
- PR #15 слит после зелёного CI; рабочий хаб обновлён (коммит хаба fd306fe),
  drift чистый.
  Session review: `ai/session-reviews/2026-09-28-hub-ignore-ds-store-closure.md`.

### 2026-09-27 — Modular architecture stage 8: all modules in `modules/`, strict boundaries (TASK-ai-dev-architecture-20260927-005)

- Closed 2026-09-27: PR #14 merged after green CI (one Codex fix: pre-confirmation
  read list in `hub-project-create`); working Hub updated after the user's "да"
  (Hub commit 5844019), drift clean; closure ran the session review through the
  new `before-task-close` event.
  Session review: `ai/session-reviews/2026-09-27-modules-strict-stage-8-closure.md`.
- `check-module-boundaries.py` gained `core`, `projects`, `tasks` in every
  module's allowed set (the three always-installed modules may reference each
  other freely); `--strict` is now called from `architecture-test.sh` and
  fails the build on any violation. Boundary warnings 27 → 0.
- Two new events in `scripts/module_passports.py` `EVENTS`: `before-task-close`
  (fired by `hub-task-finish` after Done criteria pass, before task memory is
  cleared; learning subscribes with the session review, knowledge subscribes
  with an optional never-auto-started review offer) and `after-project-create`
  (fired by `hub-project-create` after the confirmed scaffold; knowledge
  subscribes and creates the empty `knowledge/` scaffold on the same
  confirmation screen).
- `hub-project-router`, `CLAUDE.md`, `AGENTS.md` no longer name an optional
  skill directly; they resolve the planning/learning skill by role through
  `ai/modules.md`'s `## Skills` section.
- knowledge, goals, and learning moved from `hub-template/`/`scripts/` into
  `modules/<id>/{skills,scripts,data}`; then core, projects, and tasks — the
  last three modules — moved the same way, and `hub-template/` was deleted.
  Data templates keep their Hub-relative sub-path under `modules/<id>/data/`
  (e.g. `modules/core/data/ai/architecture.md`, `modules/goals/data/ai/goals.md`).
  A handful of cross-module script dependencies (e.g.
  `count-goal-progress.sh` → `archiprojects.py`,
  `check-workflow-memory.sh`/`check-hub-registry.sh`/
  `read-compact-task-index.py` → `archiprojects.py`/`calendar-date.sh`) now
  try the installed-Hub sibling path first and fall back to the other
  module's repository path, since the two scripts only sit next to each
  other after Hub installation, not in the repository source tree.
- Installed Hub target paths are unchanged: `install_pairs` target sets
  compared between commit `bd46313` (branch base) and the post-move tree are
  identical (71 targets, byte-for-byte same sorted list).
- Every live reference to `hub-template/` (scripts, tests, README.md,
  docs/concepts.md, docs/file-roles.md, ai/project-context.md,
  ai/current-task.md) was updated to `modules/…`; historical records
  (changelogs, decisions, old specs/plans, session reviews, the
  paused/future task backlog) were left as written.
- Tests: `tests/` unittest discover 184 → 188 OK; `check-consistency.sh` 0
  mismatches; `architecture-test.sh` 0 failures (was red after Task 1 by
  design, green again from Task 3 on); `hub-smoke-test.sh` unchanged
  environment-only symlink failure (green in CI); `pytest` 39 failed/265
  passed (same pre-existing environment failures as the branch baseline, 4
  more passing from the added event/passport tests). `architecture.md`
  `Version:` unchanged at `2.0` (content untouched, only its path moved).
- Decision: `ai/decisions.md` 2026-09-27 "Все модули в `modules/`, строгие
  границы" (amends 2026-08-15 and the stage-7 decision).

### 2026-09-27 — Modular architecture stage 7: architecture.md split into core + modules (TASK-ai-dev-architecture-20260927-004)

- Closed 2026-09-27: PR #13 merged after green CI; working Hub updated after
  the user's "да" (Hub commit 7b9a7e0), `hub_release.py drift` clean.
  Session review: `ai/session-reviews/2026-09-27-split-architecture-stage-7-closure.md`.
- `hub-template/ai/architecture.md` cut down to core only: ownership map,
  module-loading rules, context-loading budget, mode-based write permissions.
  `Version: 2.0`. Per-module procedures moved into six new
  `modules/<id>/rules.md` (projects, tasks, knowledge, goals, learning,
  calendar); planning gained a "Plans and reviews" section from the same split.
- Route-then-confirm is defined only in `hub-project-router`; `CLAUDE.md` and
  `AGENTS.md` now just point to it.
- A `Module rules: ai/rules/<id>.md` pointer was added to skill files of the
  affected modules (`grep -rl "Module rules:" hub-template/ai/skills modules/*/skills | wc -l` → 19).
- `check-consistency.sh` § "hub skill naming" and § "knowledge safeguards" now
  read `modules/*/rules.md` too, not just the three core files.
- Boundary warnings 55 → 27 (`check-module-boundaries.py`), because core no
  longer names other modules' skills/files in running text.
- Two duplicated planning paragraphs were dropped instead of copied (already
  stated in `modules/planning/rules.md` and `hub-workflows/SKILL.md`): the
  schedule-field/joint-confirmation paragraph, and the six-step workflow
  contract plus its "no apply mode" follow-up.
- Sizes for a typical project session (entry + router + architecture), before
  → after: `CLAUDE.md` 3757 → 3624, `architecture.md` 31969 → 7550,
  `hub-project-router/SKILL.md` 7302 → 7302 (unchanged); sum 43028 → 18476
  chars, roughly 10757 → 4619 tokens (chars/4 estimate).
- Tests: `tests/` unittest discover 180 → 184 OK (+4 new `test_rules_split`);
  `check-consistency.sh` 0 mismatches both before and after;
  `check-module-boundaries.py` 0 failures both before and after.
- Decision: `ai/decisions.md` 2026-09-27 "Правила модулей живут в
  `ai/rules/<id>.md`" (amends 2026-08-15).

### 2026-09-27 — Modular architecture stage 6: nested groups and goals (TASK-ai-dev-architecture-20260927-003)

- `scripts/archiprojects.py` (validate / tree / members); `check-hub-registry.sh`
  uses it; group id/status/fence checks kept.
- Goals in `ai/goals.md` with `group`; `count-goal-progress.sh` reads it and
  tells an unknown group from a broken registry.
- Cards keep only `primary_archiproject`; compact project index has a `group`
  column; `read-compact-task-index.py --group` reads only member projects.
- One-time migration script (validated on a temp copy, rollback on failure) run
  on the working Hub: 29 promo + 8 SEO projects, 2 goals moved, 71 cards cleaned.
- PR zykovsrg/ai-dev-architecture-template#12, CI green before merge (ca93876).
  Hub aa23ba8 (pushed): registry OK, drift 0, goal progress OK.
- Correction: the promo set is 29 projects, not 30 as first told to the user.
- Closed 2026-09-27. Session review:
  `ai/session-reviews/2026-09-27-archiprojects-groups-goals-closure.md` (issues-found, P1 rejected).

### 2026-09-27 — Modular architecture stage 5: planning and calendar modules (TASK-ai-dev-architecture-20260927-002)

- New tasks skill `hub-task-overview` (capture, overview, personal-assistant
  contract); router picks the planning skill from `ai/modules.md`.
- Events `before-task-confirmation` and `after-calendar-change`; planning rules
  `ai/rules/planning.md` own task↔calendar sync, joint change and snapshots.
- Calendar MCP: `prepare_evening_review` and `evening_review.py` removed.
- Planning and calendar moved to `modules/`; `--with/--without planning|calendar`
  installs/removes the calendar server and its `.mcp.json` entry (atomic,
  symlink-safe, every step shown in the preview).
- PR zykovsrg/ai-dev-architecture-template#11, CI green before merge (12b9182).
  Working Hub updated (6cdea19, pushed): drift 0, task records OK, both modules
  on. The calendar server needs a new session to reload.
- Boundary warnings 58 → 53. Deferred minors: calendar shell tests not in CI
  (pre-existing), untested symlink branches, bridge rebuilt on every apply.
- Closed 2026-09-27. Session review:
  `ai/session-reviews/2026-09-27-planning-calendar-modules-closure.md` (issues-found, no proposals).

### 2026-09-27 — Modular architecture stage 4: passports, Obsidian switch (TASK-ai-dev-architecture-20260927-001)

- Passports `modules/<id>/module.md` for all 10 modules; `scripts/module_passports.py`.
  The release manifest is built from passports (`RUNTIME_SCRIPTS` removed), a
  missing declared file fails loudly, targets under `projects/`/`.local/` are refused.
- Module selection persisted in `installed.json`; generated `ai/modules.md`;
  `update-installed-hub.sh --with/--without <id>` (only obsidian is switchable).
- Obsidian moved to `modules/obsidian/` with `ai/rules/obsidian.md`; task skills
  and `joint-task-change.md` use the `after-task-write` event; architecture.md 1.13.
- `scripts/check-module-boundaries.py` (warning mode, 58 warnings, none Obsidian).
- Working Hub: Obsidian disabled (Hub commits 406b01c, 15520e1); drift exit 0;
  task records OK; vault unchanged. CI green on 2738139.
- Plan `docs/superpowers/plans/2026-09-27-module-passports-obsidian-switch.md`.
- Closed 2026-09-27. Session review:
  `ai/session-reviews/2026-09-27-module-passports-obsidian-switch-closure.md`
  (issues-found, proposal P1 awaits approval).
- Deferred minors: projects passport doesn't name `archiprojects.md`; learning
  Writes mixes observations and friction notes; boundary-check GENERIC list small.

### 2026-09-27 — Modular architecture, steps 1–2 (TASK-ai-dev-architecture-20260926-001)

- Audit and spec: `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`
  (10 modules, passports, events, nested archiprojects, switch-off = not
  installed); plan `docs/superpowers/plans/2026-09-26-modular-architecture-steps-1-2.md`.
  Phases 4–8 recorded as FT-20260926-001…005.
- Drift: new `hub_release.py drift` (conflicts + unmanaged Hub files; fails on a
  missing Hub). Hub-only `calendar_task_sync.py`, newer `task_records.py`,
  `check-session-review.py`, `validate-day-plan-output.py`, 6 Hub tests and 9
  skill files brought back; `calendar-context.py`, `calendar_task_sync.py`,
  `validate-day-plan-output.py` added to `RUNTIME_SCRIPTS`. Hub updated
  (AGENTS.md, CLAUDE.md, hub-calendar/SKILL.md); drift exit 0.
- Dead code removed (~18.6k lines): `vendor/apple-calendar-mcp`, retired
  standalone updater and `smoke-test.sh`, legacy Obsidian bridge,
  `project_rule_consolidation.py`, stale `release/hub-files.json`. Plans/specs
  merged into `docs/superpowers/`.
- Fixed stale `obsidian-task-sync-test.sh` (broken since 2026-09-09, not in CI)
  and temp-dir leaks in two shell tests.
- Branch `modular-steps-1-2`, commits 519b7d3..b8b6220; every task reviewed,
  final whole-branch review fixes applied.
- Known local-only test failures: `check-consistency.sh` (untracked local
  `ai/skills/`), `hub-smoke-test.sh` (macOS `/tmp` symlink).
- Merged to `main` and pushed; CI failed once on a locale warning in
  `test-count-goal-progress.sh` (fixed in 0ccd68c, CI green).
- Session review: `ai/session-reviews/2026-09-27-modular-architecture-steps-1-2-closure.md`
  (issues-found, proposal P1 awaits approval).

### 2026-09-22 — Truthfulness and intellectual rigor instructions

- Change: added the same `Truthfulness and Intellectual Rigor` section to the
  active `AGENTS.md` and `CLAUDE.md` files and to both files under
  `hub-template/`. Agents must question and verify material claims, prioritize
  truth over agreement, state unsupported conclusions immediately, and separate
  verified facts from inference and uncertainty.
- Verification: the heading occurs exactly once in each of the four files; the
  sections have identical SHA-256 digests; `git diff --check` passed.
- Commits: `ee4b094`, `7002b41`, `d916ed5`.

### 2026-09-21 — Calendar ↔ task sync (TASK-ai-dev-architecture-20260921-001)

- Problem: a rescheduled task had to be moved by hand in both the task record
  and Apple Calendar.
- Change: optional task line `Событие: <calendar-id>/<event-id> · синхронизировано: …`;
  read-only `scripts/calendar_task_sync.py` detects calendar_moved, task_moved,
  both_moved, stale_sync, event_missing, closed_with_future_event and unlinked,
  converting event times to the calendar timezone; the day plan gains
  `## Синхронизация` and the evening review lists the same items under
  «Подтвердить». Every change stays behind the joint confirmation; `Due:` is
  never moved by sync.
- Verification: all tests pass; a real-calendar run found 3 `unlinked` items.
  Hub commits af18899..40c17f2. Spec and plan in `docs/superpowers/`.
- Deferred: recurring events are detected only by repeat dates in the window;
  a linked event turned all-day reports `event_missing`; short event titles
  (e.g. `хадасса/кардиология/…`) need a manual first link.
- Session review: `ai/session-reviews/2026-09-21-calendar-task-sync-closure.md`.

### 2026-09-18 — Shorter day plan and evening review, productive window

- Problem: the day plan ran ~90 lines. «Задачи вне календаря» mixed overdue,
  dated and undated work into one list, and «Предлагаемый календарь» restated
  the whole day. Planning ignored the user's productive hours.
- Change: the day plan is four sections — «Конфликты» and «Предлагаемый
  календарь» removed, and «Задачи вне календаря» now holds only tasks due on the
  requested date with no calendar event. The evening review is six sections —
  «Сделано», «Перенос» and «Три главных действия завтра» removed; stated
  completions and carry-overs become proposals under «Подтвердить» instead of
  narrative output. «Рекомендации» now applies the rules in
  `<hub>/ai/workflow-context.md`, where the productive window lives as data
  rather than in the workflow text, so changing the hours edits one line.
  Task weight is read only from a stated duration or the number of `## Scope`
  items, never estimated. When the window is occupied the plan may suggest one
  swap of a project work block, and never touches events with other people,
  sleep, meals or travel.
- Verification: new `tests/test-validate-day-plan-output.sh`; all six test files,
  the workflow-memory check and the task-record check pass. Today's plan
  regenerated under the new structure: 46 lines instead of ~90.
- No task record: the work was requested and done directly in conversation.
  Hub commit `2f641fd` in `personal-ai-hub`.

### 2026-09-15 — Warnings for skipped task headings

- Problem: A future task without an ID heading was silently skipped and missed
  a day plan; 55 such records existed across 9 projects.
- Change: The compact task index warns about skipped headings, the full record
  check fails on them, day plans must surface warnings, and the task record
  format now documents future and paused headings. Paused compact parsing reads
  due dates placed after `Paused:` or `Stage:` lines.
- Verification: 106 unit tests, shell tests and release manifest check passed.
- Closed 2026-09-18. Session review:
  `ai/session-reviews/2026-09-18-skipped-heading-warnings-closure.md` — result
  issues-found (F1: the delivered strict check was not invoked by any workflow;
  fixed by requiring `check-all-task-records.sh` after confirmed task-record
  writes in `hub-workflows`).

### 2026-09-15 — Scoped Obsidian forward refresh

- Change: Partial scope now refreshes only selected boards and their shared
  overview/manifest entries, without reading other projects or deleting their
  boards. Full-registry behavior and manual-edit protection remain intact.
- Installed: Updated the Hub generator and the four explicitly approved task
  workflow instructions; refreshed only their five release-manifest hashes.
- Verification: 15 synthetic-fixture tests passed against the installed script;
  the existing full Kanban contract, syntax, diff checks, and source parity passed.
- Limits: Existing local-rule-directory and release-metadata issues remain;
  the older reverse-sync suite stops at a calendar gate on both baseline and
  changed code. These unrelated fixes are deferred, not silently applied.
- Closure: User explicitly approved closure, working-Hub update, and GitHub
  publication. The current-task record now names this completed work; its ID
  was allocated at closure. Release metadata was rebuilt against existing
  source files, resolving stale metadata without changing additional rules.
- Session review: `ai/session-reviews/2026-09-15-scoped-obsidian-refresh-closure.md`.
- Details: `docs/superpowers/specs/2026-09-15-scoped-obsidian-refresh.md`.

### 2026-09-14 — Единая проверка ID задач

- Change: Все проектные ID задач теперь принимаются только в формате
  `TASK-<проект>-YYYYMMDD-NNN`; дата с дефисами отклоняется сразу.
- Impact: Генерация доски не остановится из-за записи, которую другой
  валидатор ошибочно принял.
- Verification: 87 тестов проекта, проверка канонических записей и
  предпросмотр доски прошли.

### 2026-09-13 — Часовой пояс событий Apple Calendar

- Change: Мост EventKit теперь сериализует начало и конец события в часовом
  поясе календаря, а не в UTC с ошибочной подписью локального пояса.
- Verification: регрессионные проверки календарной политики прошли; живое
  чтение вернуло время Kirov с корректным смещением `+03:00`.
- Session review: `ai/session-reviews/2026-09-13-calendar-timezone-closure.md`.

### 2026-09-10

- Change: Added and installed the guarded `prepare_evening_review` calendar tool. It gathers allowlisted calendar events, creates a noncanonical snapshot, and returns prior snapshots and pending friction for confirmation-gated learning proposals.
- Verification: 91 calendar-policy tests, assistant-workflow contract, and consistency checks passed. The full smoke test still reports the known hub entry-file size limit; the user explicitly accepted that external failure. Live review execution is deferred to 2026-09-11.

### 2026-09-10 — Явная команда обновления доски

- Change: В четырёх правилах работы с задачами явно названа команда
  `generate-obsidian-projects-kanban.sh` и её параметры обновления. Та же
  формулировка применена в рабочем хабе. Смоук-тест проверяет наличие команды
  во всех четырёх шаблонных правилах.
- Impact: После изменения записи задачи агент запускает правильный генератор,
  а не пытается передать параметры обновления сканеру доски.
- Manual checks: `smoke-test.sh`, `hub-smoke-test.sh`,
  `assistant-workflows-test.sh`, `architecture-test.sh`,
  `check-consistency.sh`, `check-hub-registry.sh`,
  `check-workflow-memory.sh`, `check-all-task-records.sh`.
- Session review: `ai/session-reviews/2026-09-10-day-editing-loop-close.md`.

### 2026-09-10 — Рекомендации по календарному контексту

- Добавлен шестой раздел дневного плана «Рекомендации».
- Описан локальный скользящий буфер: 30 прошедших дней, сегодня и 30 будущих;
  рекомендации используют прошлый месяц и следующие 14 дней.
- Первое наполнение выполняется при запуске планирования; предусмотрены
  пропуски дней, перепроверка будущих событий и неполные данные.
- Обновлены шаблон и рабочие правила. Проверка согласованности и проверка
  различий прошли; реальная выгрузка календаря в этой задаче не выполнялась.
- После проверки реального ответа добавлены явный маршрут для «остатка дня»,
  исключение day-plan из лимита 5 строк / 80 слов, исполняемый скользящий
  буфер и валидатор всех шести разделов.
- Проверка: полный `scripts/architecture-test.sh` прошёл, включая создание и
  сдвиг 61-дневного буфера и отклонение свободной сводки.

### 2026-09-10 — Дневной план синхронизирует проектные задачи

- Change: явное новое действие или напоминание, сформулированное при дневном
  планировании, получает отдельное точное предложение `create_task` или
  `update_task` для подтверждённого проекта, наряду с календарным блоком.
  При неясном проекте агент спрашивает, а не угадывает. Просроченные задачи
  выводятся только с точным каноническим названием.
- Impact: обсуждённые действия не теряются между календарём и проектом; в
  списке просроченного видно, какую именно задачу надо сделать.
- Manual checks: проверка контракта day-plan и `check-consistency` прошли;
  общий `hub-smoke-test` остановился на прежней независимой проверке portable
  install без `--root`.

### 2026-09-10 — Проверка календарного доступа перед дневным планом

- Change: календарный мост показывает в метаданных только разрешённые
  календари. Перед чтением событий дневной план обязан запросить эти
  метаданные; отсутствие ответа или отказ в доступе не выдаются за пустой
  список.
- Impact: если мост календаря недоступен, агент сообщает именно об этом; при
  доступном мосте он читает события из фактически разрешённых календарей.
- Manual checks: 89 тестов `calendar-policy`, `check-consistency` и
  `git diff --check` прошли. Полный `hub-smoke-test` остановился на прежней,
  не связанной с правкой проверке portable install без `--root`.

### 2026-09-10 — Обязательный запуск дневного плана

- Change: фразы «распланируем сегодняшний день», «план на сегодня» и `plan
  today` теперь явно распознаются как дневное планирование и обязаны вернуть
  пять разделов, без свободной сводки.
- Impact: агент не может обойти формат навыка для очевидного запроса на план.
- Manual checks: `bash scripts/check-consistency.sh`, `git diff --check` и
  статическая проверка маршрута в `hub-smoke-test.sh`.

### 2026-09-10 — Дословные названия событий в дневном плане

- Change: `day-plan` больше не пересказывает названия календарных событий.
  Существующие события копируются дословно, а у новых блоков берётся точное
  название задачи.
- Impact: «приёмка двух промо-страниц» не заменяет исходное название события.
- Manual checks: `bash scripts/check-consistency.sh`, `git diff --check` и
  статическая проверка запрета на пересказ заголовков.

### 2026-09-10 — Списки в календарях дневного плана

- Change: текущий и предлагаемый календарь в `day-plan` теперь показывают
  каждое событие отдельным пунктом, начиная со времени.
- Impact: расписание легко сканировать; события больше не сливаются в абзац.
- Manual checks: `bash scripts/check-consistency.sh`, `git diff --check` и
  статическая проверка нового списочного контракта.

### 2026-09-10 — Единый формат дневного плана

- Change: `hub-workflows` теперь выводит текущий календарь, конфликты, задачи
  вне календаря, просроченные задачи и единый предлагаемый календарь. Формат
  проверяет smoke-тест; шаблон и работающий хаб обновлены.
- Impact: агент не повторяет задачи между разделами, сохраняет события и явно
  помечает оценённую длительность предложенного блока.
- Manual checks: `bash scripts/check-consistency.sh`; статическая проверка
  контракта `hub_workflows_skill_contract_valid`; `git diff --check`.

### 2026-09-10 — Refactor, deployment and closure context

- Local main includes refactor merge fbd4c1d and combined release d40ab25.
  The parent working hub was updated; no remote push is evidenced.
- User requested closure and declined additional regression verification.
  Full integration success and complete learning preservation are not proven.
- Durable outcome and document map: `ai/refactor-handoff-2026-09-10.md`.
  Session review: `ai/session-reviews/2026-09-10-refactor-closure.md`.
- Corrected omitted memory capture after an erroneous refusal to close because
  the current-task template was empty. No task ID was invented.

Последние заметные изменения проекта.

Храни последние 2–4 недели. Старые записи переноси в `ai/archive/`.

## Шаблон

### YYYY-MM-DD

- Change:
- Impact:
- Manual checks:

## Текущий changelog

### 2026-09-05 — Хабовое закрытие задачи тоже идёт без второго подтверждения

- Change: `hub-task-finish` после проверки сразу пишет журнал изменений, решения, будущие задачи, чистит карточку задачи и сохраняет результат. Отдельное подтверждение убрано; исключение — задача с расписанием, где закрытие меняет и календарь: там остаётся один общий экран подтверждения. Правило синхронизировано в `hub-template/`, архитектура хаба повышена до 1.12.
- Impact: Хабовый путь закрытия совпал с проектным. Замечание: копии `task-finish` внутри проектов в хабовом сценарии не запускаются, поэтому правка проектного скилла касается только отдельных установок шаблона.
- Manual checks: `scripts/check-consistency.sh`, `scripts/hub-smoke-test.sh`, `scripts/check-hub-registry.sh`.

### 2026-09-05 — Закрытие задачи идёт без второго подтверждения

- Change: `task-finish` теперь после проверки сразу выполняет очистку памяти задачи и сохранение результата: журнал изменений, решения, будущие задачи, чистая карточка текущей задачи, затем коммит и пуш в GitHub. Отдельное подтверждение перед очисткой убрано; остановка возможна только когда проверка нашла блокирующую причину. Правило синхронизировано в `template/`, архитектура повышена до 7.6. Хабовый `hub-task-finish` не менялся: его подтверждение — граница безопасности хаба.
- Impact: Закрытие задачи занимает один шаг вместо двух и результат гарантированно попадает в репозиторий. Риск: очистка карточки задачи происходит без второго шанса передумать, поэтому проверка обязана быть строгой и отчёт — полным.
- Manual checks: `scripts/check-consistency.sh`, `scripts/smoke-test.sh`, `scripts/hub-smoke-test.sh`.

### 2026-09-03 — Календарь следует за задачами

- Change: `hub-task-intake`, `hub-task-switch` и `hub-task-finish` получили общий раздел синхронизации с календарём. Расписание задачи задаётся полем `Запланировано: <YYYY-MM-DD> <HH:MM>-<HH:MM>`, при его отсутствии `Due:` даёт событие на весь день. Создание задачи создаёт событие, смена расписания обновляет, закрытие удаляет будущее и не трогает прошедшее. В `hub-calendar` добавлено единственное исключение из правила «одно подтверждение на изменение»: правка памяти задачи и полное превью события показываются одним экраном и подтверждаются один раз, ровно для показанной пары. Правило продублировано в `AGENTS.md` и `CLAUDE.md`, архитектура повышена до 1.11, всё синхронизировано в `hub-template/`.
- Impact: Задачи со сроком больше не расходятся с календарём, и на это уходит одно подтверждение вместо двух. Риск: слияние шлюзов сокращает число подтверждений, поэтому превью обязано оставаться полным; при недоступности календаря не применяется ни одна из двух частей.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/check-hub-registry.sh` (в хабе).

### 2026-09-03 — Вечернее ревью по календарю

- Change: В `hub-workflows` у `evening-review` добавлены разделы «Сегодняшний календарь» и «События и проекты»: агент читает расписание запрошенного дня и связывает каждое событие максимум с одним проектом подтверждённой области по названию, схеме `категория/проект/задача` и каноническим записям задач. Уверенное совпадение даёт отдельное предложение `update_task` с точным файлом и диффом. Файл `--review-input` стал необязательным: без него «Сделано» строится из прошедших событий с пометкой «предположение из календаря». Архитектура хаба повышена до 1.10, те же правки внесены в `hub-template/`.
- Impact: Вечерний разбор работает без ручного файла ревью и сам предлагает обновление статусов. Риск: совпадение по календарю — предположение, поэтому оно не доказывает выполнение, не расширяет подтверждённую область и не применяет изменение без подтверждения.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/check-hub-registry.sh` (в хабе).

### 2026-09-01 — Жёсткое правило коротких ответов

- Change: В `AGENTS.md` и `CLAUDE.md` (рабочая копия и `template/`) мягкая строка про краткость и старый раздел `Output` с семью обязательными пунктами отчёта заменены одним разделом `Output`: лимит 5 строк по умолчанию, «сначала ответ», термины простыми словами, служебные метки (`Mode:`, имена файлов памяти, названия workflow) наружу не выносятся, один вопрос за раз. Из `ai/architecture.md` удалены разделы «Output format before changes» и «Output format after changes»; правило `## Work modes` больше не требует печатать `Mode:`. Требование сообщать об изменении памяти задачи снято по решению пользователя. Сохранено: задачу закрывает только `task-finish` после подтверждения. Те же правила внесены в хаб (`_ai-hub/AGENTS.md`, `_ai-hub/CLAUDE.md`) и в `hub-template/`, там же убран заголовок `Project:`/`Mode:`.
- Impact: Ответы агента короче и без технического жаргона, в том числе под внешними методологиями вроде Superpowers. Входные файлы выросли примерно на 35 слов, `ai/architecture.md` уменьшился примерно на 130 — суммарно контекста меньше. Риск: агент теперь не обязан сообщать, что менял файлы памяти; защита от тихой правки защищённых файлов осталась только в разделе `File Classes`.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/check-hub-registry.sh` (в хабе).

### 2026-08-29 — Настоящее расписание в дневном плане

- Change: В `hub-workflows` убрана жёсткая инструкция всегда печатать «Calendar не подключён». Дневной план и вечерний разбор читают расписание через защищённый MCP по календарям из allowlist. Добавлено правило: при недоступности MCP, отсутствии разрешения или пустом allowlist агент называет причину и не показывает пустой день. Изменение события остаётся за `hub-calendar`; `preview_change` и `apply_change` в workflows запрещены явно.
- Impact: Расписание видно сразу в плане дня. Молчание больше не выглядит как свободный день. Оба правила закреплены в контракте hub-smoke-теста, поэтому их нельзя удалить незаметно.
- Manual checks: `bash scripts/hub-smoke-test.sh` (включая два новых отклоняющих фикстура), `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/assistant-workflows-test.sh`, `bash scripts/apple-calendar-policy-test.sh`, живая проверка расписания на 30 августа.

### 2026-08-29 — Адресация одного повтора в серии

- Change: Изменение повторяющегося события теперь несёт `occurrence_start`. Мост ищет нужное вхождение в окне ±сутки и берёт то, что начинается ровно тогда; policy-слой отказывает, если найденное вхождение не совпало с запрошенным. Модель требует дату для любого recurring update или delete, предпросмотр её показывает.
- Impact: Можно отменить или изменить один день серии, не трогая остальные. Раньше идентификатор указывал на всю серию, потому что EventKit даёт всем повторам один номер.
- Manual checks: `bash scripts/apple-calendar-policy-test.sh` (62 теста), `bash scripts/apple-calendar-bridge-test.sh`, `bash scripts/calendar-policy-install-test.sh`, `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/hub-smoke-test.sh`. Живая проверка на серии «дела/приборка»: без даты возвращается начало серии 1 августа, с датой 5 и 12 сентября — соответствующие вхождения.

### 2026-08-29 — Guarded Apple Calendar MCP

- Change: Локальный Apple Calendar MCP: закреплённая копия upstream v0.9.0 с проверкой checksum, fail-closed policy-слой, одноразовые preview и семь безопасных инструментов. Мост к EventKit собран как подписанный `HubCalendarBridge.app` со своим разрешением macOS, потому что клиент MCP не может его получить. Установщик и апдейтер разворачивают инструмент в хаб; allowlist по умолчанию пуст.
- Impact: Хаб читает только явно выбранные календари. Каждое изменение события требует свежий preview и отдельное подтверждение. Прошлое событие удалить или сдвинуть нельзя. Живая установка, разрешение macOS и выбор календарей прошли как три отдельных подтверждения; выбрано шесть календарей.
- Manual checks: `bash scripts/apple-calendar-policy-test.sh` (58 тестов), `bash scripts/apple-calendar-bridge-test.sh`, `bash scripts/apple-calendar-upstream-test.sh`, `bash scripts/calendar-policy-install-test.sh`, `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/hub-smoke-test.sh`, живая проверка `calendar_status` и `read_events` через MCP.

### 2026-08-29 — Слой личного AI-ассистента над хабом

- Change: Закрыта задача проектирования ассистента: `hub-workflows` даёт day-plan, evening-review, weekly-review и capture; Bash-адаптер проверяет только механику, семантику делает агент. Записи не применяются без подтверждения.
- Impact: Персональные запросы идут в `Mode: assistant` без выбора проекта, а изменения в проектах остаются предложениями.
- Manual checks: `bash scripts/assistant-workflows-test.sh`, `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`.

### 2026-08-29 — Обзор проектов и изолированная синхронизация Obsidian

- Change: Созданы обзор всех 44 проектов и отдельные доски; `Tasks-Kanban.md` снят. Ссылки в обзоре исправлены. Обратная синхронизация теперь требует ID выбранного проекта и читает только его доску и память; наблюдатель создаёт предложение для одной доски за раз.
- Impact: Агент проекта больше не просит путь к Obsidian и не видит изменения чужих проектов. Любая правка всё ещё становится предложением и применяется только после отдельного подтверждения.
- Manual checks: `bash scripts/obsidian-task-sync-test.sh`, `bash scripts/obsidian-task-sync-watch-test.sh`, `bash scripts/obsidian-projects-kanban-test.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `git diff --check`, live `check-hub-registry.sh`.

### 2026-08-28 — Provenance и inbox knowledge-слоя

- Change: Добавлены `origin`, `valid_from` и локальный `knowledge/inbox/` в standalone и hub scaffolds; capture/review требуют явного происхождения и подтверждения действий с inbox.
- Impact: Слабые сигналы не становятся знаниями автоматически, а выводы агента отделены от прямых утверждений.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `bash scripts/hub-smoke-test.sh`, `git diff --check`.

### 2026-08-28 — Полуавтоматический self-audit архитектуры

- Change: Механизм аудита перенесён из архивного `hub-session-audit` в архитектуру: добавлены безопасный индекс metadata, методика, журнал, скрипт, тест и skill. Отдельное расписание раз в три дня использует новый скрипт.
- Impact: Точные ID пользователя разрешают чтение только выбранных сессий и безопасную запись их результата; задачи, правила, настройки и архитектура по находкам не меняются автоматически.
- Manual checks: `bash scripts/test-refresh-session-inventory.sh`, `bash scripts/check-consistency.sh`, `git diff --check`.

### 2026-08-27 — Уникальные ключи карточек Obsidian

- Change: Карточка Kanban теперь определяется парой «проект + номер задачи». Якоря имеют вид `^<project-id>--<task-id>`; одинаковые исторические `FT-` номера в разных проектах допустимы, а дубликат внутри одного проекта по-прежнему блокирует генерацию. Сканер и подтверждённое применение используют тот же ключ.
- Impact: Общая доска собирается для всех зарегистрированных проектов без ложной ошибки о дубликате и сохраняет однозначную связь карточки с канонической задачей.
- Manual checks: `bash scripts/obsidian-projects-kanban-test.sh`, `bash scripts/obsidian-task-sync-test.sh`, `bash scripts/obsidian-task-sync-watch-test.sh`, `bash scripts/check-consistency.sh`; пять мутационных проверок пойманы тестами. Пересобраны `Tasks-Kanban.md`, `Projects-Overview.md` и manifest v3; SHA проекций совпали с manifest.

### 2026-08-26 — Proposal-only workflows и recorder capture

- Change: Добавлены reusable `hub-workflows`, план дня, вечернее и недельное ревью, proposal-only capture, механические Bash guardrails и стабильный JSON-контракт `rar export/status`. Рабочий hub обновлён; изменения слиты в `main` проектов `ai-dev-architecture` и `rolling-audio-recorder`.
- Impact: Агент может разбирать подтверждённые канонические `ai/`-данные, диктовку, саммари и расшифровки, включая период записи от 1 до 120 минут, но для любого изменения показывает отдельный точный diff и ждёт именованного подтверждения. Calendar, session audit и перенос vault не включены.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/assistant-workflows-test.sh`; recorder `swift test` — 147/147 и release build. Изменения отправлены в GitHub.

### 2026-08-26 — Obsidian: Kanban задач и обзор проектов

- Change: Создана локальная копия vault в `obsidian-vault/`; в ней сгенерированы отдельные `Tasks-Kanban.md` и `Projects-Overview.md` с общим manifest. Карточка Kanban теперь равна задаче, а не проекту. Старая экспериментальная пара `Projects-Kanban.*` удалена.
- Impact: Канбан показывает статусы задач, а таблица — состояние проектов, без второй канонической базы. Ручная правка любой из двух проекций останавливает пересборку с `proposal pending`.
- Manual checks: Пользователь проверил отображение Kanban и таблицы в Obsidian. `bash scripts/obsidian-projects-kanban-test.sh` прошёл; контрольные суммы сгенерированных файлов совпали с manifest.

### 2026-08-24 — Unified assistant foundation

- Change: Завершены каноническая модель задач и архипроектов, безопасный компактный индекс, валидаторы и сохранение этих файлов при обновлении.
- Impact: Архитектура стала готовой основой для будущей Obsidian-проекции без второй базы задач и без доступа к live vault или Calendar.
- Manual checks: `bash scripts/check-consistency.sh` и `bash scripts/hub-smoke-test.sh` прошли после финальной проверки.

### 2026-08-20 — Короткие ответы простыми словами

- Change: Стиль общения усилен и закреплён. В `ai/architecture.md` (раздел «Talking to the user») добавлены правила: очень простые слова, по умолчанию короткий ответ, длинные разборы — только по запросу; отдельно указано, что правило действует и для работы под внешними методологиями (Superpowers, `code-review-graph`, плагинные скиллы). В список «Superpowers must not override» добавлен пункт `user communication style`. Строка Core Principles обновлена в `AGENTS.md` и `CLAUDE.md`. Те же правки продублированы в `template/` и в `hub-template/`, чтобы новые проекты и новый хаб получали правило сразу.
- Impact: Пользователю больше не нужно повторять просьбу «объясняй коротко и просто» в каждом чате.
- Manual checks: `bash scripts/check-consistency.sh` — все проверки OK.

### 2026-08-15 — Hub audit fixes

- Change: Fixed six defects found by an architecture audit, all sharing one theme — checks that reported success without verifying anything. `--source` is now resolved before either updater enters its target, and a source resolving to the target itself is refused; previously a relative `--source` resolved against the target, so the updater could compare a hub with itself and report "no updates". `check-hub-registry.sh` now warns on stderr about directories in `projects/` with no registry entry, leaving the exit code and stdout summary unchanged so the documented migration order (move → separate registration → validation) still works. `--check` now states in both updaters and in `--help` that it compared version numbers, not file contents. The hub updater guarantees the `/projects/` line in the hub `.gitignore` by appending it when missing, never overwriting. `hub-project-router`, `hub-registry-check` and `hub-local-router-install` are now named in `hub-template/ai/architecture.md`, and a new `[hub skill naming]` check fails if any hub skill is named in no rule file. `hub-registry-check` no longer says "each allowed root".
- Impact: Closes `FT-20260815-002`. Delivered to the live hub through `update-installed-hub.sh --apply`: three files changed (`ai/architecture.md`, `ai/skills/hub-registry-check/SKILL.md`, `scripts/check-hub-registry.sh`), hub memory untouched. The final review caught that the new skill-naming check had no test of its own — deleting it left both suites green — so test hardening was added before merge. Three smaller findings from that review are recorded as `FT-20260815-003` and were deliberately not fixed here.
- Manual checks: `check-consistency.sh`, `hub-smoke-test.sh`, `smoke-test.sh` and `check-hub-registry.sh` against the live hub all pass. Every new check was mutation-tested — deliberately broken, seen to fail, restored — including the skill-naming check against a `hub-project` probe that is a strict prefix of five real skill names.

### 2026-08-15

- Change: Added one decision rule to both architectures and all six entry files — present the clean and the cheap option together with the clean option's cost, let the user choose, and record anything deferred where it will be read again. Standalone architecture bumped to `7.2`, hub architecture to `1.4`, and the live hub updated through `update-installed-hub.sh`.
- Impact: The trade-off between a structurally clean solution and a cheaper one is now an explicit user decision instead of a silent agent choice, and deferred items cannot vanish. The broader rule the user first proposed — always choose the cleanest solution, no tech debt — was rejected after review: it contradicts the existing cost-benefit test and the ban on mixing refactoring with bug work, and today's own session produced two cases where deliberately not choosing the cleanest option was correct.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/smoke-test.sh` passed; root and `template/` copies verified identical; the live hub update was previewed with `--dry-run`, applied, and confirmed to touch only the three rule files while leaving hub memory intact; `check-hub-registry.sh` passed at 28 projects.

### 2026-08-14

- Change: Renamed all fifteen hub skills to `hub-*`, added superseded-path removal to the hub updater with symlink-component and containment guards, and added three guards covering removal safety and the prefix on both the template and the installed-hub side.
- Impact: A hub-owned skill can no longer be confused with a standalone project skill of the same name, and an installed hub still holding a pre-1.3 skill directory now fails its registry check instead of silently offering two different skills under one name.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/smoke-test.sh`, and `bash scripts/check-hub-registry.sh` against the live hub all passed. Every guard was mutation-tested: disabling it makes the covering check fail.

### 2026-08-14

- Change: Back-ported Repository Provisioning from an installed hub into `hub-template/` (architecture, both entry files, `project-create`), removed the Git contradiction it left in the hub architecture, bumped hub architecture to `1.2`, and added two installed-hub guards to `scripts/check-hub-registry.sh` — entry-file parity and required project memory files — with smoke coverage for both.
- Impact: A reinstall or hub update can no longer silently revert Repository Provisioning, and drift introduced directly in an installed hub is now detected there rather than only inside `hub-template/`. Root cause was downstream authoring: the feature never came upstream, and `check-consistency.sh` validates entry parity only in the template.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/hub-smoke-test.sh`, `bash scripts/smoke-test.sh`, and `bash scripts/check-hub-registry.sh` against the installed hub all passed. Both new guards were mutation-tested: disabling either one makes the smoke test fail.

### 2026-08-13

- Change: Added a local Markdown knowledge layer to new standalone and hub-created projects. It has `research`, `decisions`, `risks`, and `runbooks` categories; explicit capture/review workflows; confirmation-gated hub enablement for existing hub projects; and a task-finish review offer. Updater boundaries, documentation, and regression contracts were added.
- Impact: Durable project evidence can be captured and reviewed without automatic context injection, indexing, cloud services, or cross-project access. Existing hub projects remain unchanged until separately confirmed enablement. Legacy standalone migration remains deferred.
- Manual checks: `bash scripts/check-consistency.sh` and `bash scripts/smoke-test.sh` passed; final independent re-review found no P0–P3 issues.

### 2026-08-12

- Change: Added hub workflow `project-create` for confirmation-gated creation of a new project. It creates only the project's six `ai/` memory files, then its card, registry entry, and active-project selection; no Git repository, code, dependencies, project entry files, or shared skills are created.
- Impact: From `_ai-hub`, a confirmed request to create a new project now has a predictable, safe path. Existing folders remain handled by `project-register`.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, and `git diff --check` passed; independent review found and verified the self-contained template fix.

### 2026-08-12

- Change: Updated the distributable standalone and Personal AI Hub entry rules. They now require concise evidence-based communication, clear uncertainty, constructive checking of material assumptions, and the simplest sufficient solution. The entry files were shortened; detailed interpretation lives in the architecture files. Smoke tests now verify the actual `template/` installation source.
- Impact: Future installations and updates receive the same principles in standalone and hub modes without adding new skills, services, or dependencies. Hub confirmation, allowed-root, secret-handling, and memory-isolation rules remain unchanged.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, `git diff --check`; independent task and whole-branch reviews found no blocking issues.

### 2026-08-12

- Change: Released Personal AI Hub v7.0: optional `_ai-hub` installation, confirmation-gated multi-project routing, central hub workflows for project memory, project cards and signals, `info-update`, safe updates, migration preview, and Russian onboarding/English technical documentation.
- Impact: Hub-managed work starts from `_ai-hub`; project memory stays in each project and is not read before confirmation. Standalone mode remains self-contained. No local project inventory, migration, archival, cleanup, or reminder was performed.
- Manual checks: `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, and `git diff --check` passed on merged `main`; pushed to GitHub at `4f28b65`.

### 2026-07-20

- Change: Architecture v6.14 added bundled `impeccable`, `theme-factory`, `animate`, and `design-motion-principles` skills; registered Microsoft Playwright MCP as an expected external browser tool; and made `environment-check` compare the local architecture version with the repository version before offering a read-only update preview.
- Impact: New installations receive the UI/theme/motion skill set, while new sessions can detect a newer architecture without applying updates automatically. Network or MCP unavailability remains non-blocking.
- Manual checks: check-consistency passed, smoke-test passed, git diff check passed, root/template copies matched, upstream licenses were included, and the live repository comparison correctly reported local 6.14 ahead of repository 6.13.

### 2026-07-12 (3)

- Change: Лицензия репозитория заменена с MIT на PolyForm Noncommercial 1.0.0 — коммерческое использование запрещено, разрешено личное, исследовательское и некоммерческое. Текст взят дословно с raw.githubusercontent.com/polyformproject/polyform-licenses. Добавлено имя правообладателя (Sergei Zykov) вместо пустого `Copyright (c) 2026`.
- Impact: Репозиторий больше не open source в строгом (OSI) смысле; смена не ретроактивна — код, скопированный под MIT до смены, остаётся под MIT у тех, кто его скопировал.
- Manual checks: файл LICENSE прочитан целиком, сверен с официальным источником; grep по репозиторию на другие упоминания MIT — не найдено.

### 2026-07-12 (2)

- Change: v6.12+v6.13 (подтверждённые architecture-update). Superpowers повышен до критичного плагина: установка настоятельно рекомендуется, при отсутствии на баге/сложной задаче агент сначала рекомендует установку (ручной fallback — только после отказа); гейтинг сохранён. Папка `start-screen/` → `getting-started/` (устранена коллизия с именем skill). Нумерация разделов `docs/update.md` исправлена. Конвенция план-ориентированной работы перенесена: планы/спеки Superpowers теперь в `ai/superpowers/plans|specs` (рабочая память рядом с changelog/decisions), а не в `docs/`; исторические планы шаблона перемещены в `archive/superpowers/`. Версия 6.13.
- Impact: `docs/` содержит только документацию; вся память задач собрана в `ai/`; установка Superpowers — ожидаемый шаг для каждого проекта.
- Manual checks: check-consistency OK, smoke-test passed, cmp root/template (AGENTS, CLAUDE, architecture) identical, проверка ссылок (0 битых), grep по `docs/superpowers` (0 живых ссылок вне архива и истории).

### 2026-07-12

- Change: README переписан пользователем в новом стиле, опечатки исправлены, универсальный стартовый промт перенесён в README (раздел «Установка в проект»); папка `prompt/` удалена (промежуточное имя `start-here/` тоже); `docs/start-here.md` → `start-screen/start-screen.md`; все 9 файлов `docs/` переведены на английский (docs — техническая часть, README и start-screen — русские, для людей); заголовок и вводные разделы `ai/architecture.md` (root+template) переведены на английский по правилу «AI-facing instructions in English» (подтверждённый architecture-update; цитаты русских фраз пользователя сохранены); все внутренние ссылки обновлены. Удалена выполненная FT-20260711-005 (репозиторий стал публичным; история проверена на секреты — чисто). Ранее в сессии удалены устаревшие ветки codex/on-demand-start-screen (локально+worktree) и origin/architecture-onboarding-task-flow.
- Impact: Публичный репозиторий показывает актуальную структуру; стартовый промт доступен прямо в README без перехода по ссылкам; языковая политика единообразна.
- Manual checks: check-consistency (9+9 holders OK), smoke-test passed, cmp root/template architecture.md identical, grep по старым путям (0 живых ссылок), проверка относительных ссылок (0 битых), grep истории на секреты (чисто).

### 2026-07-11 (4)

- Change: Реализованы FT-004, FT-006, FT-002. `task-finish` Phase 2: запись promoted-задачи удаляется из `ai/future-tasks.md` при закрытии (след в changelog); `task-switch` и правила `future-tasks.md` согласованы. `task-finish` Rules/Phase 3: при наличии `github.com` remote commit+push — обязательные шаги закрытия, не default. `README.md` переписан в инфостиле (~130 строк вместо 249), инвентарь 11 base skills сверен, добавлена ссылка на uninstall, определение «другой задачи» обновлено до границы по Done criteria. Удалены реализованные записи FT-001, FT-003 (и по новому правилу FT-002/004/006) из бэклога.
- Impact: Бэклог не копит закрытые задачи; закрытие задачи гарантированно синхронизирует GitHub; README читается новичком.
- Manual checks: check-consistency (17+17 holders OK), cmp root/template для task-finish и task-switch, copy-review чек-лист по README, git status по составу.

### 2026-07-11 (3)

- Change: Ужесточена модель разделения задач. `task-intake` и `task-switch` теперь используют один тест — «попадает ли запрос в записанные Done criteria текущей задачи» — вместо семи размытых признаков; добавлен обязательный вопрос с 3 вариантами (расширить/переключиться/future-tasks) для запросов вне границы. Core Rules в AGENTS.md/CLAUDE.md дополнены одной строкой. `ai/architecture.md` v6.11. Merged to `main` и запушено.
- Impact: Новый запрос по умолчанию считается другой задачей; тихое расширение scope текущей задачи больше невозможно без явного обновления Goal/Done criteria.
- Manual checks: smoke-test, check-consistency, git diff --check, cmp для 5 пар root/template, размер entry-файлов (+99 байт, лимит 110, строк не прибавилось), Codex/Claude паритет. Ручной сценарий из плана (проверка в свежей сессии) отложен по решению пользователя.

### 2026-07-11 (2)

- Change: Added a single self-contained universal start prompt (`prompt/README.md`) covering both install and update; linked it from README.md, docs/install.md, docs/update.md, docs/start-here.md, docs/start-prompts.md. Merged to `main` and pushed (commit `a90ff40`).
- Impact: Users can copy one prompt (linkable directly via GitHub's folder README rendering) and their agent decides install vs update automatically.
- Manual checks: smoke-test, check-consistency, file confirmed present on GitHub via `gh api`. Repo is private, so anonymous `raw.githubusercontent.com` links return 404 for unauthenticated users — link only works for collaborators with access.

### 2026-07-11

- Change: Added on-demand `start-screen` base skill (11 base skills now), routing lines in entry files, architecture.md v6.10 rule, environment-check registration, docs inventories update, and `docs/uninstall.md` safe removal guide. Merged to `main` and pushed (commit `a84559b`).
- Impact: Users can request a short Russian orientation screen; it never shows automatically. Removal guidance now exists.
- Manual checks: smoke-test, check-consistency, root/template `cmp` for 5 file pairs, entry-file size budget (+41 bytes/file). Deferred: fresh-session prompts "Покажи стартовый экран" and environment-check independence.

### 2026-07-10

- Change: Installed the architecture into this repository root so the architecture can be used to evolve itself.
- Impact: Root `AGENTS.md`, `CLAUDE.md`, and `ai/*` now hold project-specific working memory; `template/` remains the distributable user template.
- Manual checks: Installation completed with `scripts/install.sh .`; project context filled for self-development.
### 2026-08-29 — Legacy project Obsidian bridge

- Change: Added a guarded installer and contract test that add the central
  Obsidian reverse-sync bridge to registered version-7.3 projects. The bridge
  derives the enclosing hub, uses the scoped central board, and remains
  proposal-only until the user confirms a proposal hash. All 33 installed
  legacy projects now have the bridge; the divergent Goal Planner macOS entry
  files received it without replacing their existing content.
- Impact: A project opened directly from the hub no longer needs a manually
  supplied vault path for the supported reverse-sync flow. Standalone copies
  still do not infer a vault.
- Manual checks: legacy bridge contract passed; all 33 version-7.3 projects
  contain the bridge in both entry files; scoped scan command accepted the
  `zdorove-businki` board and produced a validation-blocked proposal without
  writing canonical records.
