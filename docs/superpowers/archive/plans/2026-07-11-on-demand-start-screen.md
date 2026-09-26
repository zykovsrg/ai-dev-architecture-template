# On-Demand Start Screen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a short Russian start screen that appears only on explicit request, explains the architecture in plain language, and shows the current project task.

**Architecture:** Add one required read-only `start-screen` skill and keep its detailed behavior out of the always-loaded entry files. Route explicit start/help requests to the skill with one line in `AGENTS.md` and `CLAUDE.md`, mirror all reusable architecture files under `template/`, and keep `environment-check` independent except for verifying and listing the new skill.

**Tech Stack:** Markdown skills and architecture docs, Bash smoke tests, Git.

---

## File Structure

- Create `ai/skills/start-screen/SKILL.md`: activation, reads, output contract, safety rules, and concise Russian screen template.
- Create `template/ai/skills/start-screen/SKILL.md`: installation-template mirror.
- Modify `AGENTS.md`, `CLAUDE.md`, `template/AGENTS.md`, and `template/CLAUDE.md`: one routing line only.
- Modify `ai/architecture.md` and `template/ai/architecture.md`: version bump, base-skill catalog entry, and detailed on-demand behavior.
- Modify `ai/skills/environment-check/SKILL.md` and its template mirror: verify and advertise `start-screen` without displaying it automatically.
- Modify `scripts/smoke-test.sh`: verify installation includes the new required skill.
- Modify `README.md`, `docs/install.md`, and `docs/prompts.md`: keep required-skill inventories accurate.
- Create `docs/uninstall.md`: safe human-readable removal guidance.
- Modify `docs/start-here.md`: link to removal guidance.

### Task 1: Add a failing installation check

**Files:**

- Modify: `scripts/smoke-test.sh:47-51`

- [ ] **Step 1: Add the required-skill assertion**

Insert after the existing `task-intake` assertion:

```bash
assert_file "$PROJECT/ai/skills/task-intake/SKILL.md"
assert_file "$PROJECT/ai/skills/start-screen/SKILL.md"
assert_not_exists "$PROJECT/ai/skills/bugfix-workflow/SKILL.md"
```

- [ ] **Step 2: Run the smoke test and verify it fails for the missing skill**

Run:

```bash
bash scripts/smoke-test.sh
```

Expected: exit code `1` with `missing file: .../ai/skills/start-screen/SKILL.md`.

- [ ] **Step 3: Commit the failing test**

```bash
git add scripts/smoke-test.sh
git commit -m "test: require start screen skill on install"
```

### Task 2: Create the read-only `start-screen` skill

**Files:**

- Create: `ai/skills/start-screen/SKILL.md`
- Create: `template/ai/skills/start-screen/SKILL.md`

- [ ] **Step 1: Create the canonical skill**

Create `ai/skills/start-screen/SKILL.md` with this content:

```markdown
---
name: start-screen
type: knowledge
description: |
  Show a short plain-language introduction to the AI development architecture and the current project task.
  Activates when the user explicitly asks "покажи стартовый экран", "с чего начать", "как работать с архитектурой", "что умеет эта архитектура", or similar.
  Does NOT activate automatically at session start, during environment-check, or for a request to list every installed skill or tool.
---

# Start Screen

Use this skill only after an explicit user request. It is a read-only orientation screen, not a workflow and not an environment audit.

## Read

- `ai/current-task.md`
- `ai/future-tasks.md`
- `ai/external-tools.md`

Use the currently available skill/tool catalog when the platform exposes one. If availability cannot be verified, describe only the configured project categories and label external availability as not confirmed.

## Output principles

- Write in Russian for a non-developer.
- Use information style: short sentences, concrete verbs, no promotional filler.
- Keep the whole answer close to one normal screen.
- Explain technical terms in plain language or omit them.
- Show categories and important examples, not the full skill catalog.
- End with the live current-task snapshot.
- Do not repeat the full `environment-check` report.

## Required sections

Use these headings and adapt the content to the current project:

### Что это

Explain in no more than two short sentences that the architecture keeps project context in files, helps AI agents continue work without losing task state, and protects scope.

### Как идёт работа

Explain briefly:

- project memory lives in `ai/` files;
- one task is current;
- unfinished work can be paused;
- future ideas are saved separately;
- task completion requires user confirmation and a saved result.

### С чего начать

Show no more than six useful commands:

- `task-intake` — start and record a new task;
- `task-switch` — pause, resume, or switch work;
- `task-finish` — verify and finish the current task after confirmation;
- `environment-check` — check architecture files and external capabilities;
- `start-screen` — show this screen again;
- "Покажи все skills и инструменты" — show the full catalog separately.

### Что доступно

Use compact categories:

- project workflows for tasks, reviews, tests, security, releases, and architecture changes;
- optional or external skills for specialized work;
- external tools for code analysis and controlled methodologies such as Superpowers, only when present or configured.

Do not print every skill name. Offer the full-catalog request instead.

### Как удалить

Say that removal is a separate confirmed operation. Tell the user to ask "Помоги удалить архитектуру". Before deletion, the agent must show the affected files, offer to preserve or back up project memory, distinguish rules from task history, and request explicit confirmation. Link to `docs/uninstall.md` when it exists. Never delete anything while showing the start screen.

### Сейчас в проекте

For `ai/current-task.md`, show only:

- short goal;
- `Status`;
- `Stage`;
- next step or blocker.

If `Status: empty`, say there is no active task and suggest `task-intake`.

For future tasks, mention only the count when easy to determine. Do not print the backlog.

## Safety

- Do not edit files.
- Do not activate `task-intake`, `task-switch`, `task-finish`, installation, update, or removal automatically.
- Do not claim an external tool is installed unless availability is verified.
- Do not expose secrets, raw configuration, or full task-memory files.
```

- [ ] **Step 2: Create the template mirror**

Copy the same content into `template/ai/skills/start-screen/SKILL.md` using `apply_patch`, then verify exact equality:

```bash
cmp ai/skills/start-screen/SKILL.md template/ai/skills/start-screen/SKILL.md
```

Expected: exit code `0` and no output.

- [ ] **Step 3: Run the smoke test**

```bash
bash scripts/smoke-test.sh
```

Expected: `Smoke tests passed.`

- [ ] **Step 4: Commit the skill**

```bash
git add ai/skills/start-screen/SKILL.md template/ai/skills/start-screen/SKILL.md
git commit -m "feat: add on-demand start screen skill"
```

### Task 3: Route explicit requests without growing entry files

**Files:**

- Modify: `AGENTS.md:65-70`
- Modify: `CLAUDE.md:65-70`
- Modify: `template/AGENTS.md:65-70`
- Modify: `template/CLAUDE.md:65-70`

- [ ] **Step 1: Add one routing line to each entry file**

Add immediately before the `environment check` trigger in all four files:

```markdown
- start: ai/skills/start-screen/SKILL.md
```

Do not copy the screen template or detailed behavior into these files.

- [ ] **Step 2: Verify root/template parity**

```bash
diff -u AGENTS.md template/AGENTS.md
diff -u CLAUDE.md template/CLAUDE.md
```

Expected: no differences.

- [ ] **Step 3: Verify Codex/Claude semantic parity**

Run:

```bash
diff -u AGENTS.md CLAUDE.md
```

Expected: only the existing tool-specific wording differs; both contain the identical `start-screen` routing line.

- [ ] **Step 4: Enforce the size budget**

Record the post-change sizes:

```bash
wc -l -w -c AGENTS.md CLAUDE.md
```

Expected: each file grows by one line and no more than 42 bytes from the baseline (`AGENTS.md` 4,246 bytes; `CLAUDE.md` 4,254 bytes). If either exceeds that budget, shorten the routing line before continuing.

- [ ] **Step 5: Commit the routing rule**

```bash
git add AGENTS.md CLAUDE.md template/AGENTS.md template/CLAUDE.md
git commit -m "docs: route explicit requests to start screen"
```

### Task 4: Add the detailed architecture rule and base-skill registration

**Files:**

- Modify: `ai/architecture.md:1-100,356-370`
- Modify: `template/ai/architecture.md:1-100,356-370`

- [ ] **Step 1: Bump the architecture version**

Change in both files:

```markdown
Version: 6.10
```

- [ ] **Step 2: Add the on-demand start-screen rule**

Insert after the session-start/environment-check section and before work-mode continuation:

```markdown
### On-demand start screen

The start screen is separate from `environment-check`. Show it only after an explicit user request such as "покажи стартовый экран", "с чего начать", or "как работать с архитектурой". Never show it automatically at a session boundary or during a repeated environment check.

Use `ai/skills/start-screen/SKILL.md`. The screen is read-only, uses plain Russian for a non-developer, stays close to one normal screen, and ends with the current task goal, `Status`, `Stage`, and next step or blocker. It shows skill/tool categories only; the full catalog is a separate request.
```

- [ ] **Step 3: Register the base skill**

Add to the `Base skills` list in both files:

```markdown
- `start-screen` — short read-only orientation shown only after an explicit user request.
```

- [ ] **Step 4: Verify exact root/template equality**

```bash
cmp ai/architecture.md template/ai/architecture.md
```

Expected: exit code `0` and no output.

- [ ] **Step 5: Commit the architecture rule**

```bash
git add ai/architecture.md template/ai/architecture.md
git commit -m "docs: define on-demand start screen behavior"
```

### Task 5: Make installation and environment checks aware of the skill

**Files:**

- Modify: `ai/skills/environment-check/SKILL.md:41-56,167-190`
- Modify: `template/ai/skills/environment-check/SKILL.md:41-56,167-190`
- Modify: `README.md:35-55`
- Modify: `docs/install.md:46-66`
- Modify: `docs/prompts.md:160-195,255-290`

- [ ] **Step 1: Add `start-screen` to required base skills**

Add this path to both environment-check skill files after `task-intake`:

```markdown
- `ai/skills/start-screen/SKILL.md`
```

- [ ] **Step 2: Add it to the informational menu without activating it**

Add to the base menu in both environment-check skill files:

```markdown
- `start-screen` — по явному запросу кратко объяснить архитектуру и показать текущую задачу; автоматически не показывается.
```

- [ ] **Step 3: Update the documented inventories**

Add `start-screen/SKILL.md` next to the other base skills in `README.md`, and add `ai/skills/start-screen/SKILL.md` to every complete required-skill list in `docs/install.md` and `docs/prompts.md`. Change any text that says "10 base skills" to "11 base skills".

- [ ] **Step 4: Verify environment-check mirrors**

```bash
cmp ai/skills/environment-check/SKILL.md template/ai/skills/environment-check/SKILL.md
```

Expected: exit code `0` and no output.

- [ ] **Step 5: Run installation and consistency checks**

```bash
bash scripts/smoke-test.sh
bash scripts/check-consistency.sh
```

Expected: `Smoke tests passed.` and `All canonical lists are consistent.`

- [ ] **Step 6: Commit installation metadata**

```bash
git add ai/skills/environment-check/SKILL.md template/ai/skills/environment-check/SKILL.md README.md docs/install.md docs/prompts.md scripts/smoke-test.sh
git commit -m "docs: register start screen as base skill"
```

### Task 6: Add safe removal guidance

**Files:**

- Create: `docs/uninstall.md`
- Modify: `docs/start-here.md:1-45`

- [ ] **Step 1: Create the uninstall guide**

Create `docs/uninstall.md` with this content:

```markdown
# Как удалить архитектуру

Не удаляйте папку `ai/` целиком без проверки. В ней может храниться история текущих, приостановленных и будущих задач, решения проекта и журнал изменений.

Попросите агента: `Помоги удалить AI development architecture`.

Перед изменениями агент должен:

1. показать файлы, которые относятся к архитектуре;
2. отметить файлы, где может быть содержимое проекта;
3. предложить резервную копию памяти задач;
4. спросить, нужно убрать только правила или также историю задач;
5. показать итоговый план удаления;
6. получить отдельное подтверждение.

Безопасный вариант по умолчанию — убрать правила и skills архитектуры, но сохранить копию `ai/current-task.md`, `ai/paused-tasks.md`, `ai/future-tasks.md`, `ai/project-context.md`, `ai/decisions.md` и `ai/changelog.md`.

`AGENTS.md`, `CLAUDE.md`, `.claude/` и `.codex/` могут содержать не только файлы этой архитектуры. Агент должен изменить их выборочно, а не удалять целиком.
```

- [ ] **Step 2: Link it from the start guide**

Add this short section to `docs/start-here.md`:

```markdown
## Удаление архитектуры

Сначала прочитайте [безопасную инструкцию по удалению](uninstall.md). Не удаляйте `ai/`, `AGENTS.md`, `CLAUDE.md`, `.claude/` или `.codex/` целиком без проверки содержимого.
```

- [ ] **Step 3: Commit the removal documentation**

```bash
git add docs/uninstall.md docs/start-here.md
git commit -m "docs: add safe architecture removal guide"
```

### Task 7: Verify the complete behavior and architecture safety

**Files:**

- Review: all files changed by Tasks 1-6

- [ ] **Step 1: Run automated checks**

```bash
bash scripts/smoke-test.sh
bash scripts/check-consistency.sh
git diff --check HEAD~6..HEAD
```

Expected: both scripts pass and `git diff --check` prints nothing. If the actual commit count differs, replace `HEAD~6` with the commit before Task 1.

- [ ] **Step 2: Verify all root/template mirrors**

```bash
cmp AGENTS.md template/AGENTS.md
cmp CLAUDE.md template/CLAUDE.md
cmp ai/architecture.md template/ai/architecture.md
cmp ai/skills/environment-check/SKILL.md template/ai/skills/environment-check/SKILL.md
cmp ai/skills/start-screen/SKILL.md template/ai/skills/start-screen/SKILL.md
```

Expected: all commands exit `0` with no output.

- [ ] **Step 3: Recheck entry-file size**

```bash
wc -l -w -c AGENTS.md CLAUDE.md
```

Expected: one added line per file and no more than 42 added bytes per file relative to the recorded baseline.

- [ ] **Step 4: Manually simulate an explicit start-screen request**

Use this test prompt in a fresh agent turn:

```text
Покажи стартовый экран.
```

Expected output:

- Russian plain language;
- approximately one screen;
- six required sections;
- no full environment audit;
- no full skill catalog;
- correct current goal, status, stage, and next step;
- removal guidance requires preview and confirmation;
- no files changed.

- [ ] **Step 5: Manually verify environment-check independence**

Use this test prompt:

```text
Проведи проверку окружения.
```

Expected: normal environment snapshot and menu; no `Что это` start-screen introduction.

- [ ] **Step 6: Review protected-file authorization and working tree**

```bash
git diff --name-only HEAD~6..HEAD
git status --short
```

Expected: only confirmed architecture, template, test, and documentation files changed; working tree clean except controlled task memory if it is intentionally ignored by Git.

- [ ] **Step 7: Update task handoff for review**

Through the active `architecture-update` workflow, set `ai/current-task.md` to `Stage: review` and record checks, remaining risks, and the proposal to run `task-finish`. Do not mark the task done.
