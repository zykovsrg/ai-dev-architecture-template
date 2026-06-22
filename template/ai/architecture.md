# Архитектура AI-разработки

Version: 6.9

Этот файл — справочник по workflow и иерархии правил. Его не нужно загружать для каждой задачи. Читай его только если задача касается workflow, конфликтов правил, architecture-update или если правило неясно.

## Главная идея

Контекст должен жить в репозитории, а не только в чате.

- Чат — временная рабочая память.
- `AGENTS.md` и `CLAUDE.md` — короткие входные файлы для AI-агентов.
- `ai/current-task.md` хранит текущую задачу.
- `ai/paused-tasks.md` хранит незавершённые задачи, поставленные на паузу через `task-switch`.
- `ai/future-tasks.md` хранит идеи и будущие задачи, которые не входят в текущий scope.
- `ai/project-context.md` хранит проектный контекст.
- `ai/decisions.md` хранит устойчивые решения и инварианты.
- `ai/changelog.md` хранит последние заметные изменения.
- `ai/skills/*/SKILL.md` хранит переиспользуемые процедуры.
- Git хранит полную историю изменений.

Главное правило для идей на потом:

```text
Future tasks are captured, not executed.
```

Если во время работы появляется полезная идея вне текущей задачи, агент должен защитить текущий scope: предложить записать идею в `ai/future-tasks.md`, но не реализовывать её без явного promotion.

Главное правило для новой работы:

```text
Every real task goes through task-intake first.
```

Если `ai/current-task.md` пустой, новая задача должна быть записана туда до начала работы. Если там уже есть незавершённая задача, агент должен решить, это продолжение или переключение через `task-switch`.

## Режимы работы

Before starting task work, the agent must explicitly state the mode as `Mode: ...`.

- `implementation` — менять код, проектные файлы, тесты или task memory.
- `review` — читать файлы, проверять состояние проекта или diff, пересказывать контекст, сообщать о проблемах или предлагать следующий шаг; не редактировать файлы.
- `task-finish` — проверять завершение задачи и чистить контекст только после подтверждения.
- `architecture-update` — предлагать изменения архитектуры разработки; менять файлы только после подтверждения.

If the mode is unclear, the agent must ask or state the assumption before acting.

Use `review` when the agent only reads files, summarizes context, inspects project state, runs `environment-check`, or suggests the next step without editing.

Use `implementation` only when the agent is going to change application code, project files, tests, or task memory.

If implementation or review suggests the current task may be complete, the agent must not declare the task closed. It must propose `task-finish` and wait for user confirmation.

## Session start check

`environment-check` is not a work mode.

`task-intake` and `task-switch` are also not work modes. `task-intake` captures new work into task memory. `task-switch` protects unfinished work when the user changes focus.

Run `environment-check` before suggesting next steps or starting implementation when:

- the architecture was just installed;
- entering an existing project;
- switching tools or agents;
- continuing in a new chat;
- continuing from compressed, compacted, restored, or summarized context.

Compressed context, compacted context, restored summary, and conversation summary continuation count as a new session for this rule.

Skip only if the user explicitly says not to run `environment-check`.

This check is not a deep audit. It is a quick availability check.

After a successful `environment-check`, before the menu, the agent must show a short snapshot of the current task (title, `Status`, `Stage`, next step or blocker) and a compact summary of future tasks. This snapshot is informational and must not edit task memory or activate any workflow.

Then the agent must show a short "Available next commands and skills" menu.

The menu must include only available workflows/skills relevant to this architecture, for example:

```text
- `environment-check` — re-run the installation and environment availability check.
- `task-intake` — record the first task or decide whether a new request continues or switches the current task.
- `task-switch` — pause the current task, resume a paused task, or promote a confirmed future task.
- `task-finish` — verify whether the current task is complete and run cleanup only after confirmation.
- `architecture-update` — propose and apply approved architecture changes.
- `Superpowers` — required path for bugs and complex tasks when available.
- `future-tasks` — record useful ideas that should not expand the current task scope.
```

This menu is informational. The agent must not start any listed workflow automatically unless the user explicitly chooses it.

After `environment-check`, continue in one of the work modes:

- `implementation`
- `review`
- `task-finish`
- `architecture-update`

Before the first real task after `environment-check`, run `task-intake`.

## Architecture files and task memory

### Protected architecture files

Protected architecture files define reusable agent rules, workflows, tools, and architecture. They may be changed only in `architecture-update` mode and only after explicit user confirmation.

<!-- canon:protected-files -->
- `AGENTS.md`
- `CLAUDE.md`
- `ai/architecture.md`
- `ai/external-tools.md`
- `ai/skills/*/SKILL.md`
- `.claude/`
- `.codex/`
<!-- /canon:protected-files -->

Do not edit protected architecture files during normal implementation, review, init, cleanup, task-finish, task-switch, or external skill/tool workflows.

External skills, external tools, init workflows, setup commands, and generated recommendations may propose changes to protected architecture files, but must not apply them without confirmation.

### Controlled memory files

Controlled memory files store project and task memory. They are not protected architecture files, but they may be edited only by the matching workflow.

<!-- canon:controlled-memory -->
- `ai/current-task.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`
- `ai/project-context.md`
- `ai/decisions.md`
- `ai/changelog.md`
<!-- /canon:controlled-memory -->

Allowed edits:

- `implementation`: may update `ai/current-task.md` when the current task itself changes, Stage changes, or needs handoff notes.
- `implementation`: may update `ai/future-tasks.md` only when the user explicitly asks to save a future task or confirms a proposed future task candidate.
- `task-intake`: may create or update `ai/current-task.md` when it is empty and the user has provided a real task.
- `task-switch`: may update `ai/current-task.md` and `ai/paused-tasks.md` only after explicit user confirmation.
- `task-switch`: may promote an entry from `ai/future-tasks.md` into `ai/current-task.md` after explicit user confirmation.
- `task-finish`: may update `ai/current-task.md`, `ai/changelog.md`, `ai/decisions.md`, and confirmed `ai/future-tasks.md` entries only after explicit user confirmation.
- `architecture-update`: may update controlled memory files if the approved architecture change requires it.
- `ai/project-context.md`: update only after confirmation when stack, commands, structure, data model, invariants, or fragile zones change.

Before finishing any task, check the diff with:

```bash
git diff --name-only
```

If protected architecture files changed without explicit `architecture-update` confirmation, stop and ask the user before continuing.

If controlled memory files changed, explain which workflow allowed the change and list the exact files in the final report.

## Canonical lists and the consistency check

The protected-files and controlled-memory lists are duplicated in a few "holder"
files: `ai/architecture.md`, `CLAUDE.md`, `AGENTS.md`, `docs/file-roles.md`, and the
`release-check` skill. Each copy is wrapped in invisible HTML-comment markers, for example
`<!-- canon:NAME -->` … `<!-- /canon:NAME -->` where NAME is `protected-files` or `controlled-memory`.

`scripts/check-consistency.sh` compares the file paths inside matching markers across
all holders and fails if any copy drifts. Run it after editing any marked list. It is
also run by `architecture-update` and `release-check`.

This script lives in the architecture template repository and is NOT copied into
installed projects. Inside a project the marker comments are harmless but inert, and
the consistency check simply does not apply — `architecture-update` and `release-check`
skip it when the script is absent.

Human docs (`README.md`, other `docs/*`) do not repeat these lists; they link to
`docs/file-roles.md`. When you add a new copy of a canonical list, wrap it in the same
markers so the check covers it.

## Current task status and stage

`ai/current-task.md` must separate task state from work stage.

Use `Status` for task state:

```text
empty / active / review / blocked / done / paused
```

Use `Stage` for work stage:

```text
intake / spec / planning / implementation / review / task-finish
```

Do not write free-form status like `spec done, planning next` into `Status`.

When moving into implementation, update `Stage: implementation` if task memory is being maintained in this project.

When task-finish cleanup leaves a blank task template, use:

```text
Status: empty
Stage: intake
```

## Main files

### AGENTS.md

Entry file for Codex.

Keep it short: first-level rules, context routing, skill triggers, work modes, and output format.

### CLAUDE.md

Entry file for Claude Code.

It should match `AGENTS.md` in meaning.

### ai/current-task.md

One current task.

Keep it short: roughly one screen.

### ai/paused-tasks.md

Short list of tasks paused through `task-switch`.

This is not a backlog. Use it only for unfinished tasks that need to be resumed.

### ai/future-tasks.md

Backlog of ideas and future implementation tasks that are useful but outside the current task scope.

This is not active work and not paused work.

Use it for:

- ideas discovered during implementation or review;
- non-blocking follow-up investigations;
- missing test seams that are useful but outside the current task;
- larger refactors or improvements that should not expand the current scope;
- user requests like `запиши на потом`, `добавь в будущие задачи`, `потом надо сделать`.

Do not use it for:

- unfinished active work — use `ai/paused-tasks.md` through `task-switch`;
- completed change history — use `ai/changelog.md`;
- durable decisions and invariants — use `ai/decisions.md`;
- blocking cleanup needed before the current task can close — keep it in `ai/current-task.md` or handle it before `task-finish`.

Allowed statuses:

```text
idea / ready / blocked / promoted / done / dropped
```

A future task can become active only after explicit user instruction or confirmation. When promoted, copy it into `ai/current-task.md` and mark the original entry as `promoted`.

### ai/project-context.md

Project context:

- what the project is;
- stack;
- run, build, and test commands;
- important folders and files;
- main screens or modules;
- data model or key entities;
- project invariants;
- fragile zones.

Target length: up to 150 lines.

If project-context content becomes stale, do not only mention it in chat or changelog. Propose a project-context update and wait for confirmation.

### ai/decisions.md

Only important active decisions.

Use it for durable architecture decisions, product rules, data model constraints, storage rules, signing/sandboxing requirements, undo/sync invariants, and decisions future agents must not accidentally break.

Do not use it for minor bugfixes, colors, spacing, or ordinary change history.

### ai/changelog.md

Recent notable project changes.

Keep the last 2–4 weeks. Move old entries to `ai/archive/`.

### ai/external-tools.md

Expected external skills, tools, and controlled methodologies, including source URLs for installation.

Used by `environment-check`.

Missing optional skills and external tools are warnings, not blockers.

## Changelog vs decisions vs future tasks

Use `ai/changelog.md` for what changed recently.

Use `ai/decisions.md` for what future agents must not forget or break.

Use `ai/future-tasks.md` for what may be useful later but is not part of the current task.

Put long-term rules in `ai/decisions.md`, not only in `ai/changelog.md`, when they affect:

- data model;
- storage location or migration;
- signing, sandboxing, entitlements, deployment, or local setup;
- undo or redo behavior;
- sync behavior;
- recurrence, scheduling, or time logic;
- external APIs;
- architecture boundaries;
- agent workflow that must persist across sessions.

Do not write future plans into `ai/changelog.md` as if they were completed work.

Do not write durable rules into `ai/future-tasks.md`; future tasks are work items, not decisions.

## Language

Persistent AI-facing instruction files should be in English:

- `AGENTS.md`
- `CLAUDE.md`
- `ai/skills/*/SKILL.md`

Repository reference and memory files may be in Russian or English:

- `ai/current-task.md`
- `ai/project-context.md`
- `ai/architecture.md`
- `ai/decisions.md`
- `ai/changelog.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`

## Talking to the user (beginner-friendly)

The user is not a developer. Write to someone who is just starting to learn IT.

- Communicate in Russian.
- Do not assume any prior development knowledge.
- Explain every technical term in plain words the first time it appears in a reply. This includes everyday-for-developers words like commit, diff, merge, branch, rollback, dependency, environment, schema, cache.
- Do not just say what you will do — explain why, in simple steps, so the user understands the logic, not only the action.
- Prefer short, concrete analogies when they make an idea clearer.
- Avoid unexplained jargon, English-only tech words without a gloss, and dense abbreviations.
- If a concept is unavoidably complex, break it into small numbered steps.
- It is better to over-explain than to leave the user guessing.

This rule applies to all user-facing communication, including mode statements, risk notes, and final reports. It does not change the language of persistent AI-facing instruction files, which stay in English.

## Skills

Base skills:

- `task-intake` — captures a new user task into `ai/current-task.md`, detects whether a request is a continuation or a different task, and routes unfinished-task changes to `task-switch`.
- `ui-review` — user-visible UI, layout, visual states, interaction feedback.
- `security-review` — security risks.
- `release-check` — pre-commit, pre-merge, build, or release review.
- `copy-review` — user-facing text.
- `write-tests` — test decision and tests for risky changes.
- `task-finish` — closing a task and cleaning context after confirmation.
- `task-switch` — switching between unfinished tasks without losing context; may promote confirmed future tasks into current work.
- `architecture-update` — updating development architecture after user approval.
- `environment-check` — checking architecture installation, tool availability, and printing the available next commands/skills menu.

Use skills by trigger. Do not apply skills from memory. Open the current `ai/skills/*/SKILL.md` before using that workflow.

Open only the skill that matches the current task. Do not load all skills automatically.

### UI changes and tests

For UI behavior, screen state, layout logic, scrolling, rendering logic, or interaction changes, use `ui-review` and `write-tests`.

For purely decorative visual changes, use `ui-review`. Use `write-tests` only if behavior, state, layout logic, accessibility, or interaction can be affected.

If automated tests are not practical for a UI change, provide a manual UI checklist.

### Task intake

For every real user task, use `task-intake` before starting work.

If `ai/current-task.md` has `Status: empty`, `task-intake` records the task in `ai/current-task.md` before implementation or review begins.

If `ai/current-task.md` contains unfinished work and the user's request changes the goal, work mode, main files, Done criteria, or deliverable, `task-intake` must stop and invoke `task-switch`.

If the request is only a clarification, test, review, or finish step for the current goal, continue the current task and update Stage or handoff notes only when useful.

### Bugfix, performance, and complex work

This architecture no longer includes a local `bugfix-workflow` skill.

For bugs, crashes, regressions, flaky behavior, debug requests, performance investigations, large/vague tasks, major refactors, data model changes, migrations, TDD-heavy tasks, or unclear blast radius, use Superpowers when available.

If Superpowers is missing or not confirmed, the agent must say that the task normally requires Superpowers and ask whether to install/configure it or continue with a manual fallback.

Do not pretend there is still a local bugfix workflow. Do not create `CONTEXT.md`, `docs/adr/`, or another parallel documentation system unless the project explicitly requires it.

There is no separate `Mode: bugfix`. Treat bug work as:

```text
Mode: implementation
Workflow: task-intake + Superpowers
```

The task must still use this repository's sources of truth: `ai/current-task.md` for scope, `ai/decisions.md` for durable invariants, `ai/future-tasks.md` for non-blocking follow-up ideas, and `task-finish` for closure.

### Future task capture

Use future task capture when a useful idea appears but does not belong to the current confirmed scope.

Typical triggers:

- `запиши на потом`;
- `добавь в будущие задачи`;
- `потом надо сделать`;
- `давай позже реализуем`;
- a useful non-blocking improvement appears during implementation, review, Superpowers-driven bug work, or task-finish.

If the user explicitly asks to save it, append it to `ai/future-tasks.md`.

If the idea appears implicitly, propose the future task first and wait for confirmation before editing.

A future task entry should include:

- short title;
- status;
- priority if clear;
- source or context;
- proposed task;
- acceptance criteria;
- promotion notes if needed.

Do not implement a future task unless the user explicitly promotes it to the current task.

### Active decision check

Before committing a new service, resolver, storage path, undo path, sync behavior, data model change, or architecture-sensitive logic, read relevant active entries in `ai/decisions.md`.

If the implementation contradicts an active decision, stop and propose `architecture-update`.

### Optional project skills

Optional project skills may be installed only in projects where they are useful. They are not required base skills and must not make `environment-check` fail when absent.

- `frontend-design` — optional project skill for UI composition, visual hierarchy, frontend component design, and UX improvements. Use only for UI/frontend/design tasks when `ai/skills/frontend-design/SKILL.md` is installed. Source URL lives in `ai/external-tools.md`.

External skills and tools do not replace base skills.

Expected external skills/tools:

- `code-review-graph` — main tool for code review and blast-radius analysis when available. Source URL lives in `ai/external-tools.md`.
- `agent-skills-for-context-engineering` — additional context-engineering skills.

Controlled external methodologies:

- `Superpowers` — checked at startup; required for bugs and complex tasks when available.

## Skill precedence

Workflow priority:

1. `AGENTS.md` / `CLAUDE.md`
2. `ai/current-task.md`
3. relevant base skill
4. optional project skills and expected external skills/tools
5. controlled external methodologies

Optional project skills, external skills, and tools help the agent, but do not control the workflow. They must not override work mode, confirmation rules, `task-finish`, `architecture-update`, `environment-check`, clean architecture principle, or project-specific rules in `ai/project-context.md`.

## code-review-graph priority

For complex review or unclear blast radius, check whether `code-review-graph` is available.

Use `code-review-graph` when available for:

- multi-module changes;
- new services, resolvers, adapters, or domain logic;
- architecture-sensitive changes;
- complex bugs;
- large pre-merge reviews;
- unclear affected files;
- dependency analysis that is hard to trace manually.

Do not require it for:

- small copy changes;
- simple visual tweaks;
- narrow bugfixes with known relevant files.

If it should be used but is not available, report this as a warning, not a blocker by default.

## Context and tokens

Do not read the whole `ai/` folder automatically.

Default minimum context:

- `AGENTS.md` or `CLAUDE.md`
- `ai/current-task.md`

Read `ai/project-context.md` only if the task concerns project behavior, architecture, storage, screens, or if `current-task` asks for it.

Read `ai/decisions.md` only for architecture-sensitive tasks, durable invariants, or release checks where relevant.

Read `ai/future-tasks.md` only when the user asks to capture, review, promote, search, or clean future tasks, or when a workflow explicitly needs it.

Read `ai/architecture.md` only if the task concerns workflow, development architecture, rule conflicts, architecture-update, or if a rule is unclear.

For plan-driven or Superpowers tasks, read only relevant files:

- `docs/superpowers/specs/<spec>.md`
- `docs/superpowers/plans/<plan>.md`
- when needed — this architecture section about plan-driven work.

Do not read `ai/archive/` without a concrete reason.

## Output format before changes

Before editing, the agent should:

1. State the mode: `Mode: ...`.
2. Briefly explain in simple words what it will do next.
3. Name important risk only if there is one.

Do not list technical files before editing unless it helps the user understand the change or the user asked for file names.

## Scope control

Do not expand user-confirmed scope.

If it becomes useful to do more, stop and ask before adding new scope.

If a useful idea is outside the current task, capture it as a future task candidate instead of implementing it.

If a user request changes goal, work mode, relevant files, Done criteria, or creates a separate deliverable, decide whether `task-switch` is needed.

Small UI iterations can stay inside one task if they clarify the same goal. If they create a new goal, use `task-switch`.

## Review fact check

In `review` mode, do not report a problem as fact until it is verified with read, grep, diff, logs, tests, or another concrete check.

If not verified, label it as a hypothesis.

Do not create work from stale assumptions. Re-check the file before saying that an issue still exists.

## Output format after changes

After editing, the agent should:

1. Start the report with the used mode, for example `Mode: implementation`.
2. Briefly describe what changed.
3. List checks.
4. Name risks or unfinished parts.
5. Explicitly say whether task memory changed.
6. If the task looks complete, propose `task-finish`, not declare the task closed.

If task memory changed, list exact files:

- `ai/current-task.md`
- `ai/changelog.md`
- `ai/decisions.md`
- `ai/project-context.md`
- `ai/paused-tasks.md`
- `ai/future-tasks.md`

## Clean architecture principle

Do not accumulate technical debt and temporary solutions.

Temporary workarounds are allowed only as exceptions. If a workaround is used:

1. Mark it as temporary workaround.
2. Explain why it is needed now.
3. Explain what risk it creates.
4. Add a follow-up: what to replace, where, and when.
5. Decide whether to record it in `ai/changelog.md`, `ai/decisions.md`, or `ai/future-tasks.md`.

Do not fix bugs in a way that worsens data model, screen consistency, or project readability.

If a clean solution takes more time, offer two options:

- quick safe fix;
- proper architecture solution.

## Temporary diagnostics lifecycle

Temporary diagnostic code in main is allowed only if intentionally kept for the next step.

If TEMP diagnostics remain in main, create an explicit removal record in one of:

- `ai/paused-tasks.md` if the active task is being paused through `task-switch`;
- Done criteria of `ai/current-task.md`;
- `ai/changelog.md` during confirmed `task-finish` cleanup.

The record must include:

- diagnostic code location;
- why it remains;
- when to remove it;
- removal criteria;
- risk if it stays too long.

A note buried inside an unrelated task is not enough for committed TEMP diagnostics.

Do not use `ai/future-tasks.md` for required TEMP diagnostic cleanup if the current task cannot safely close without that cleanup.

## Plan-driven work with Superpowers

This section applies only to tasks explicitly done through Superpowers planning, writing-plans, subagent-driven-development, or similar plan-driven workflow.

Ordinary tasks do not have to use these rules.

### Source of truth for progress

For plan-driven work, `docs/superpowers/plans/<plan>.md` is the source of truth for execution progress.

- Do not use internal TodoWrite, harness task lists, TaskCreate, TaskUpdate, or chat history as the only progress source.
- After completing each plan task, update the checkbox in `docs/superpowers/plans/<plan>.md`.
- If a plan task is partially done, leave the checkbox empty and add a short `Note:` under the task.
- If a task is cancelled or moved, mark it with a short `Note:`.

Example:

```markdown
- [x] Task 2 — Add app wrapper
  - Note: chose minimal wrapper over Xcode project to avoid restructuring Package.swift.
- [ ] Task 3 — Add UI smoke tests
  - Note: blocked until .app bundle launches reliably.
```

The controller agent in subagent-driven work is responsible for keeping the plan file updated. It must not rely only on subagent status or harness task state.

### Measurement before spec for bugs and performance

For bug and performance tasks, do a reproduction or measurement pass before writing a spec when practical.

If the spec is based on a hypothesis, mark it explicitly:

```text
Hypothesis: unproven
Measurement needed before implementation: yes
```

### Local decisions

Record small judgment calls inside the relevant plan task with `Note:`.

Use `ai/decisions.md` only for durable architecture, product, workflow, or data model decisions.

Do not duplicate the same decision in plan notes, `ai/decisions.md`, and `ai/changelog.md`.

Choice rule:

- `docs/superpowers/plans/<plan>.md` — local reasons inside one plan.
- `ai/decisions.md` — decisions future agents must remember outside the current plan.
- `ai/changelog.md` — notable final changes, not every micro-step.
- `ai/future-tasks.md` — future work that should not expand the current plan unless promoted.

### Commit convention

For plan-driven commits, use a verifiable convention:

```text
Plan Task <N>: <short action>
```

Examples:

```text
Plan Task 1: add app bundle wrapper
Plan Task 2: add Info.plist generation
Plan Task 3: add UI smoke test target
Plan Cleanup: update task handoff
```

If a commit closes several plan tasks, use a range:

```text
Plan Tasks 4-5: add bundle smoke checks
```

Prefer one logical plan task per commit by default.

### Handoff between agents

If an agent stops in the middle of plan-driven execution, it should leave a quick handoff at the end of the plan or in `ai/current-task.md`:

- last completed plan task;
- next plan task;
- known blockers;
- latest relevant commits.

Do not create a separate progress file without a clear reason. Plan progress lives in the plan file.

## Task switching

`task-intake` decides whether a request is new, continued, or future work. Use `task-switch` when `ai/current-task.md` contains an unfinished task and `task-intake` classifies the user request as a different task.

Do not overwrite `ai/current-task.md` automatically.

First show:

1. Current unfinished task.
2. New requested task.
3. Risk of switching.
4. Options:
   - continue current task;
   - pause current task and start a new one;
   - finish current task through `task-finish`;
   - discard current task and replace it;
   - promote a future task into `ai/current-task.md`.

Only update `ai/current-task.md` after explicit user confirmation.

### How to detect a different task

A new request is a different task if:

1. Goal changes.
2. Work mode changes.
3. Main files or project area change.
4. Done criteria change.
5. New request does not help complete the current task.
6. New request creates a separate deliverable.
7. Current task would remain unfinished after the new request.

A new request is the same task if it clarifies, narrows, tests, reviews, or completes the current goal.

If unsure, ask:

```text
Похоже, это новая задача, а текущая ещё не закрыта. Переключаемся или продолжаем текущую?
```

If the current task is paused, write a short entry to `ai/paused-tasks.md`.

Do not use `ai/paused-tasks.md` as a backlog. Use `ai/future-tasks.md` for future ideas and tasks.

## Task finish and saving work

Closing a task means both:

1. The task is verified and task memory is cleaned through `task-finish`.
2. The result is saved.

Default save behavior:

- If a GitHub remote is configured, create a commit and push the branch to GitHub after confirmed `task-finish` cleanup.
- If Git is available but GitHub is not configured, create a local commit and tell the user that the work is saved only on this computer.
- If Git is unavailable, create a clear local fallback such as a patch or archive and tell the user where it is.

Do not claim that a task is closed until the save step is complete or the user explicitly accepts a local-only fallback.

## Architecture update

Use `architecture-update` when a reusable rule, workflow, project constraint, skill, or architecture principle needs to change.

Before changing files, show:

1. What changes.
2. What it changes to.
3. Exact files.
4. Exact wording.
5. Token impact.
6. Why it belongs there.

Then ask: `Replace this?`

Do not update architecture files without explicit user confirmation.

If stale architecture or project memory is discovered during a task, do not only mention it as a warning. Propose an `architecture-update` task or project-context update and wait for confirmation.

## Revision rhythm

After each task:

- update `ai/changelog.md` if there was a notable change;
- update `ai/decisions.md` if an important durable decision appeared;
- add confirmed out-of-scope follow-up work to `ai/future-tasks.md`;
- clean `ai/current-task.md` only after user confirmation.

Weekly:

- shorten `ai/changelog.md`;
- move old entries to `ai/archive/`;
- review `ai/future-tasks.md` and mark stale tasks as `dropped` after confirmation.

Monthly:

- review `AGENTS.md` and `CLAUDE.md`;
- for each line ask: “If this line is deleted, will the agent start making mistakes?”;
- if the answer is no, delete it;
- review skills and remove stale or duplicate rules.

## Superpowers gated use

Superpowers may be installed and checked, but it is a controlled external methodology.

Superpowers may be proposed for:

- bugs, crashes, regressions, flaky behavior, debug requests, and performance investigations;
- large or vague tasks;
- architecture design;
- choosing between technical options;
- data model changes;
- migrations;
- TDD;
- subagents;
- major refactoring;
- unclear blast radius.

Superpowers should be used for bugs and complex tasks when available. For other work, it may be activated when:

- the user explicitly asks to use it;
- the user explicitly confirms the agent's proposal to use it;
- `ai/current-task.md` says `Use Superpowers: yes`.

For a bug or complex task, state that Superpowers is the expected path and use it when it is available. If it is unavailable, ask whether to install/configure it or continue manually.

Do not use Superpowers for:

- copy changes;
- simple UI tweaks;
- narrow tasks with known relevant files;
- `task-finish`;
- `environment-check`;
- `architecture-update`, unless the user explicitly asks.

Superpowers must not override:

- work mode;
- `ai/current-task.md`;
- user confirmation rules;
- `task-finish` rules;
- `environment-check` rules;
- `architecture-update` rules;
- clean architecture principle;
- project-specific rules in `ai/project-context.md`.

If Superpowers suggests a heavier workflow, first propose it to the user and ask for confirmation.
