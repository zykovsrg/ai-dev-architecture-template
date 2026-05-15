# Changelog

## v4.0 — 2026-05-15

- Added `docs/start-prompts.md`.
- Added two ready-to-copy start prompts:
  - first architecture installation in a project;
  - starting a new chat inside an already configured project.
- Linked `docs/start-prompts.md` from `README.md`.

## v3.9 — 2026-05-15

- Final hierarchy cleanup after architecture review.
- Merged duplicate `Session start check` sections in `ai/architecture.md`.
- Removed `task-switch` from the post-environment-check work mode list.
- Confirmed `task-switch` remains a safety workflow, not a work mode.
- Work modes remain: `implementation`, `review`, `task-finish`, `architecture-update`.


## v3.8 — 2026-05-15

- Added explicit criteria for detecting whether a new user request is a different task.
- Updated `task-switch`, `ai/architecture.md`, README, and docs with task-difference rules.
- Confirmed that `task-switch` remains a safety workflow, not a work mode.
- Base skills count remains 10.


## v3.7 — 2026-05-15

- Added `task-switch` as a new base skill.
- Added `ai/paused-tasks.md` for intentionally paused unfinished tasks.
- Clarified that `task-switch` is not a work mode; it is a safety workflow for switching between unfinished tasks.
- Added rules preventing silent overwrite of unfinished `ai/current-task.md`.
- Base skills count increased from 9 to 10.


## v3.6 — 2026-05-15

- Clarified that `environment-check` is not a work mode.
- Work modes remain limited to `implementation`, `review`, `task-finish`, and `architecture-update`.
- Added a separate session-start explanation for `environment-check`.
- Added `Use Superpowers: no` to `ai/current-task.md` as an explicit gated flag.


## v3.5 — 2026-05-15

- Removed Graphify from active architecture after uninstall.
- Removed Graphify from entry files, external tools, environment-check, release-check, README, and docs.
- Kept historical Graphify mentions in CHANGELOG.md only.
- `code-review-graph` remains the primary expected external tool for code review and blast-radius analysis.


## v3.4 — 2026-05-15

- Cleaned hierarchy conflicts after adding controlled Superpowers.
- Fixed `ai/architecture.md` work modes and base skills descriptions.
- Replaced old external-tools section with current hierarchy:
  - expected external skills/tools
  - controlled external methodologies
  - optional external alternatives
- Fixed duplicated numbering in `environment-check`.
- Updated `release-check`: `code-review-graph` is now the primary suggestion for code blast-radius review; Graphify is only for broader project/document mapping.


## v3.3 — 2026-05-15

- Kept Superpowers in the architecture as a controlled external methodology.
- Superpowers is checked during environment check but must not activate by default.
- Added Superpowers gated-use rules: explicit user request or `Use Superpowers: yes` in `ai/current-task.md`.
- Clarified that Superpowers must not override work mode, confirmation rules, task-finish, architecture-update, clean architecture principle, or project-specific rules.
- Graphify remains an optional external alternative.


## v3.2 — 2026-05-15

- Added skill precedence rule: internal architecture files define workflow priority, external skills/tools are helpers.
- Added `environment-check` to the required base skills list in entry files.
- Normalized wording from optional external tools to expected external skills/tools.
- Removed Superpowers from expected external tools because it is a full external methodology that can conflict with the lightweight workflow.
- Made `code-review-graph` the primary expected external tool for code review and blast-radius analysis.
- Demoted Graphify to optional external alternative for broad project/document mapping.


## v3.1 — 2026-05-15

- Added `ai/external-tools.md`.
- Environment check now verifies expected external skills and tools:
  - Graphify
  - Superpowers
  - agent-skills-for-context-engineering
  - code-review-graph
  - claude-seo
- Missing external tools are reported clearly but are not blockers.
- Agent must not install missing external tools without explicit user confirmation.


## v3.0 — 2026-05-15

- Added first-session environment check.
- Added new base skill: `environment-check`.
- Agent must check required base skills and optional external tools at the start of a new project session.
- Required base skills count increased from 8 to 9.
- Optional external tools are not blockers and must not be installed automatically.


## v2.9 — 2026-05-15

- Added Graphify as an optional external tool.
- Graphify is recommended only for large, unfamiliar, or high-blast-radius tasks.
- Added optional Graphify guidance to `README.md`, `docs/concepts.md`, `docs/file-roles.md`, `docs/update.md`, `ai/architecture.md`, and `release-check`.
- Base skills remain unchanged: 8 skills.


## v2.8 — 2026-05-14

- Сокращён общий шаблон `AGENTS.md` и `CLAUDE.md`.
- Сжаты разделы `Project context`, `Context routing`, `Output style` и `Task intake reminder`.
- В постановке задачи оставлен блок `Relevant files`.
- Из напоминания о постановке задачи убран блок `Constraints`.
- Подробные правила про язык файлов оставлены в `ai/architecture.md`; в общем шаблоне оставлена короткая строка про инструкции для ИИ на английском.

## v2.7 — 2026-05-14

- Project invariants вынесены из `AGENTS.md` и `CLAUDE.md`.
- Добавлен короткий блок `Project context` со ссылкой на `ai/project-context.md`.
- Уточнено, что проектные правила не нужно дублировать в верхнеуровневых файлах агентов.

## v2.6 — 2026-05-14

- Усилен режим `architecture-update`: перед заменой правила агент должен показать `current rule → proposed rule → exact files`.
- Добавлено явное подтверждение замены: `Replace this?`.
- Синхронизация Google Doc заменена на синхронизацию документации в репозитории.

## v2.5 — 2026-05-14

- Путь локального шаблона по умолчанию изменён на `~/Documents/ai-dev-architecture-template`.

## v2.4 — 2026-05-14

- Добавлена пошаговая инструкция установки и обновления.
- Этап создания и синхронизации шаблона объединён в один процесс.

## v2.3 — 2026-05-12

- Зафиксированы 4 внешних skills и инструмента:
  - `code-review-graph`
  - `agent-skills-for-context-engineering`
  - `superpowers`
  - `claude-seo`

## v2.2 — 2026-05-11

- `task-completion-check` и `task-cleanup` объединены в `task-finish`.
- Количество базовых skills уменьшено с 9 до 8.

## v2.1 — 2026-05-11

- В `release-check` добавлен Materiality check.

## v2.0 — 2026-05-11

- Добавлено версионирование.
- Расширены descriptions у skills: добавлены явные триггеры и не-триггеры.
- Во frontmatter skills добавлен `type`: `knowledge`, `worker` или `mixed`.
- Добавлено месячное правило ревизии `AGENTS.md` и `CLAUDE.md`.

## v1.0

- Первая версия архитектуры одиночной AI-разработки.
