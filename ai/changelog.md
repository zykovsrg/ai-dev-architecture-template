# Changelog

Последние заметные изменения проекта.

Храни последние 2–4 недели. Старые записи переноси в `ai/archive/`.

## Шаблон

### YYYY-MM-DD

- Change:
- Impact:
- Manual checks:

## Текущий changelog

### 2026-10-04 — Session learning installed

- Change: hub-session-scan skill, transcript collector and rule catalog with
  deterministic confidence/scope; learned-rules files read by new chats; day
  plan offers a scan; weekly review shows the learning report and merge pass.
- Impact: Claude Code (Haiku 4.5) and Codex (GPT-6-Luna) scan the same
  sessions once; weekly pass on Opus 5.5 / GPT-6.1-Sol.
- Validation: 48 learning tests, architecture suite, consistency and strict
  boundary checks pass; live scan in both tools; second run 0 pending.

### 2026-10-03 — Guided evening review installed

- Change: urgent-first review conversation and installed read-only selector.
- Impact: projectless events skip without questions; outcomes are asked one
  event at a time; repeated blocks of a covered task are not asked again.
- Validation: 26 planning tests, 197 main tests, module boundary checks,
  optional module removal and installation smoke pass. Guarded live input
  verifies the installed helper. Four managed Hub files installed; no test
  changed Calendar events.
- Closure 2026-10-04: TASK-ai-dev-architecture-20261003-001 closed by user
  request; task records pass. Session review:
  ai/session-reviews/2026-10-04-guided-evening-review-closure.md
  (insufficient-evidence, implementation session not visible).

### 2026-10-02 — Calendar-first day plan, three sections

- Closure: completed by user request; session review found no issue within the
  selected implementation span. No historical task ID is fabricated.
- Session review: ai/session-reviews/2026-10-02-calendar-first-day-plan-closure.md.

- Change: synchronize linked task times before composing, reload canonical state,
  and verify affected records after joint edits. Calendar is authoritative for
  time; deadlines and completion remain user decisions.
- Output: current calendar, synchronization, overdue tasks (last). Removed
  task-outside-calendar and recommendation sections; analysis still uses learned
  rules, numeric goals and guarded calendar context.
- Validation: output acceptance/rejection tests, 8 scenario tests, 20 Calendar
  task-sync tests, consistency and strict module-boundary checks pass.
- Deployment: applied the reviewed 8-file Hub update; installed format and
  registry checks pass (73 projects). Calendar bridge rebuilt with a writable
  temporary compiler cache after its default cache was denied by the sandbox.


### 2026-10-02 — PR #19 слит, хаб обновлён (FT-20261001-003)

- PR #19 слит после зелёного CI и двух исправлений по ревью Codex.
- Хаб: коммит синхронизации инструкций и реестра, затем обновление
  (коммит хаба 14ce754: `calendar_drift.py`, `review_proposals.py`).
  `--check`: хаб совпадает с исходниками; реестр проходит (73 проекта).

### 2026-10-01 — Аудит архитектуры и самообучение (TASK-ai-dev-architecture-20261001-002)

- Отчёт: `docs/audits/2026-10-01-architecture-audit.md`.
- PR #17 (слит): правки хаба 871efdb и «план дня из 5 разделов» перенесены в
  `modules/`; восстановлены шаги 5–6 `hub-task-finish`; `hub-project-create`
  не входит в новый проект без запроса на переключение.
- PR #18 (слит): удалён `migrate-archiprojects-stage6.py`, 7 записей
  `promoted`; старый журнал и 93 плана/спеки — в архив.
  `refresh-session-inventory.sh` оставлен (его вызывает автоматизация).
- PR #19 (открыт): `calendar_drift.py` (расхождения утро/вечер → журнал,
  повторы для недельного обзора) и `review_proposals.py` (висящие предложения
  разборов во всех проектах; узкое исключение доступа по решению пользователя).
- Session review: `ai/session-reviews/2026-10-01-architecture-audit-closure.md`.

### 2026-10-01 — Чистка проектов от копий архитектуры (TASK-ai-dev-architecture-20261001-001)

- Закрыты как уже выполненные: FT-20260812-001 (миграция в хаб, 72 проекта зарегистрированы) и FT-20260813-001 (standalone-путь удалён из шаблона, см. CHANGELOG).
- FT-20260815-001 взята в работу как TASK-ai-dev-architecture-20261001-001.
- TASK-ai-dev-architecture-20261001-001 закрыта: из 33 проектов хаба удалены 17 общих скиллов-копий и `ai/external-tools.md` (кроме проектов со своими скиллами); указатели `AGENTS.md`/`CLAUDE.md`/`ai/architecture.md` сохранены и закоммичены; свои скиллы и `.claude/` не тронуты. Session review: `ai/session-reviews/2026-10-01-legacy-project-cleanup-closure.md`.


### 2026-09-28 — Выключаемые knowledge, goals, learning; Python 3.9; документация (TASK-ai-dev-architecture-20260928-002)

- Closed 2026-09-28: PR #16 merged after green CI (two Codex rounds);
  working Hub updated (Hub commit 108721d), drift clean.
  Session review: `ai/session-reviews/2026-09-28-optional-modules-switch-docs-closure.md`.
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
- `sync-calendar-policy.sh` ставил сервер календаря, но никогда не создавал
  его `.venv` — на свежей установке сервер не мог запуститься. Установка
  теперь сама создаёт `.venv` (берёт Python 3.11+ из `HUB_CALENDAR_PYTHON`
  или PATH, при сбое убирает недособранную `.venv`), если её ещё нет; готовую
  не трогает. `HUB_CALENDAR_SKIP_VENV=1` пропускает шаг в фикстурных тестах —
  теперь выставлен во всех тестах, запускающих install/update, чтобы CI не
  требовал сети. `modules/calendar/tests/calendar-venv-install-test.sh`
  проверяет создание, пропуск для уже готовой `.venv`, очистку при сбое и
  текст `--dry-run` (увиден падающим до правки).

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
- Plan `docs/superpowers/archive/plans/2026-09-27-module-passports-obsidian-switch.md`.
- Closed 2026-09-27. Session review:
  `ai/session-reviews/2026-09-27-module-passports-obsidian-switch-closure.md`
  (issues-found, proposal P1 awaits approval).
- Deferred minors: projects passport doesn't name `archiprojects.md`; learning
  Writes mixes observations and friction notes; boundary-check GENERIC list small.

### 2026-09-27 — Modular architecture, steps 1–2 (TASK-ai-dev-architecture-20260926-001)

- Audit and spec: `docs/superpowers/specs/2026-09-26-modular-architecture-design.md`
  (10 modules, passports, events, nested archiprojects, switch-off = not
  installed); plan `docs/superpowers/archive/plans/2026-09-26-modular-architecture-steps-1-2.md`.
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
- Details: `docs/superpowers/archive/specs/2026-09-15-scoped-obsidian-refresh.md`.

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


## 2026-10-02 — Approved architecture corrections

Task: TASK-ai-dev-architecture-20261002-001.
Corrected calendar/task identity and recurring-instance matching, preserved recurrence in the calendar bridge, validated schedule dates and ranges, and preserved legacy all-day records. Consolidated write policy, added project-memory readiness instructions, and enabled separately confirmed cleanup for registered projects. Full architecture checks and 94 calendar-policy tests passed. Installed Hub matches source; bridge rebuilt. Other projects and live calendar data remain unverified. Detailed result: docs/audits/2026-10-02-refactoring-assessment.md.


## 2026-10-02 — Preserve legacy schedule compatibility

Confirmed project-compatibility inspection exposed trailing comments and start-only schedules rejected by the new strict parser. Added regression coverage and preserved both existing forms while still validating real dates/times; no end time is invented. 196 main unit tests, 29 calendar-sync tests and 5 sync-field tests passed. Corrected parser installed in Hub. Individual compatibility findings remain in each confirmed project's ai/hub-compatibility-2026-10-02.md, without copying task details here.


## 2026-10-02 — Architecture corrections closed

Task: TASK-ai-dev-architecture-20261002-001.
All remaining 66 active projects inspected within the user-confirmed manifest;
all six memory files present and task records canonical. Updated 58 exact
legacy pointers across 29 projects. Context gaps in 41 projects are recorded
for factual follow-up. Two additional legacy schedule forms preserved;
197 current main tests pass, installed Hub matches source.
Guarded live planning initialized 61-day context, reconciled 11 linked task
schedules across nine files, and verified affected dates. No Calendar event,
deadline or completion-status change was made by synchronization.
Reports: docs/audits/2026-10-02-all-project-compatibility.md; per-project
ai/hub-compatibility-2026-10-02.md. Live calendar artifacts stay in Hub ai/tmp
and are not committed. Session review: ai/session-reviews/2026-10-02-architecture-corrections-closure.md; issues-found with partial Luna chronology coverage.
Work saved locally; no remote push or main-branch merge claimed.
