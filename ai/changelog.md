# Changelog

Последние заметные изменения проекта.

Храни последние 2–4 недели. Старые записи переноси в `ai/archive/`.

## Шаблон

### YYYY-MM-DD

- Change:
- Impact:
- Manual checks:

## Текущий changelog

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
