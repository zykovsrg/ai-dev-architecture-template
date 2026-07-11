# Strict Task Boundary Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flip the task-classification presumption: a new request is a different task by default unless it fits the recorded Done criteria of the current task.

**Architecture:** Rewrite the decision sections of `task-intake` and `task-switch` around one objective test (recorded Done criteria), add a mandatory three-option question for out-of-boundary requests, amend one existing Core Rules line in the four entry files, and register the rule in `ai/architecture.md` v6.11. All root files mirror to `template/`. Repository invariant: root `AGENTS.md`, `CLAUDE.md`, `ai/` are git-excluded working copies; only `template/`, docs, and scripts are committed.

**Tech Stack:** Markdown skills and architecture docs, Bash verification scripts, Git.

**Spec:** `docs/superpowers/specs/2026-07-11-strict-task-boundary-design.md`

**Baselines:** `AGENTS.md` 4287 bytes / 99 lines; `CLAUDE.md` 4295 bytes / 99 lines; `ai/architecture.md` has `Version: 6.10`.

---

## File Structure

- Modify: `AGENTS.md`, `CLAUDE.md`, `template/AGENTS.md`, `template/CLAUDE.md` — one-line amendment only.
- Modify: `ai/skills/task-intake/SKILL.md` + `template/ai/skills/task-intake/SKILL.md` — rewrite "Existing unfinished current task".
- Modify: `ai/skills/task-switch/SKILL.md` + `template/ai/skills/task-switch/SKILL.md` — rewrite "How to decide" and the UI-iteration rule.
- Modify: `ai/architecture.md` + `template/ai/architecture.md` — version bump and "Task boundary" section.

### Task 0: Create the feature branch

- [ ] **Step 1: Branch**

```bash
git checkout -b strict-task-boundary
git status --short
```

Expected: clean tree, new branch active.

### Task 1: Amend the Core Rules line in the four entry files

**Files:**

- Modify: `AGENTS.md`, `CLAUDE.md`, `template/AGENTS.md`, `template/CLAUDE.md`

- [ ] **Step 1: Replace the line in all four files**

In each file replace exactly:

```markdown
- Prefer minimal diffs, clean architecture, and confirmed scope.
```

with:

```markdown
- Prefer minimal diffs, clean architecture, and confirmed scope; a request beyond the recorded Done criteria is a different task until the user confirms otherwise.
```

- [ ] **Step 2: Verify parity and size budget**

```bash
diff AGENTS.md template/AGENTS.md && diff CLAUDE.md template/CLAUDE.md && echo PARITY_OK
wc -l -c AGENTS.md CLAUDE.md
```

Expected: `PARITY_OK`; still 99 lines per file; `AGENTS.md` ≤ 4397 bytes, `CLAUDE.md` ≤ 4405 bytes (growth ≤ 110 bytes, no new lines).

- [ ] **Step 3: Verify Codex/Claude semantic parity**

```bash
diff AGENTS.md CLAUDE.md
```

Expected: only the pre-existing tool-specific wording differs; both contain the identical amended line.

- [ ] **Step 4: Commit**

```bash
git add template/AGENTS.md template/CLAUDE.md
git commit -m "docs: define task boundary by recorded Done criteria in core rules"
```

Note: root `AGENTS.md`/`CLAUDE.md` are git-excluded working copies; only template mirrors are committed. This applies to every commit in this plan.

### Task 2: Rewrite the decision section in task-intake

**Files:**

- Modify: `ai/skills/task-intake/SKILL.md`
- Modify: `template/ai/skills/task-intake/SKILL.md`

- [ ] **Step 1: Replace the "Existing unfinished current task" section**

In `ai/skills/task-intake/SKILL.md` replace the entire section (from the `## Existing unfinished current task` heading up to, not including, `## Bugs and complex tasks`):

````markdown
## Existing unfinished current task

A new request is a different task by default.

Treat it as a continuation ONLY if it fits the recorded Done criteria of the
current task, meaning at least one of:

1. It directly advances the recorded Done criteria.
2. It fixes or adjusts work just produced for this task.
3. It runs tests, checks, or review of this same work.
4. It answers a question the agent asked.

Everything else is a different task, even if it touches the same files or the
same screen. Do not start work. Ask one question with three options and wait:

```text
Этот запрос выходит за Done criteria текущей задачи. Как поступим?
1. Расширить текущую задачу — я обновлю Goal и Done criteria в ai/current-task.md.
2. Переключиться на новую задачу через task-switch.
3. Записать в ai/future-tasks.md и продолжить текущую задачу.
```

If the user chooses to extend, update `Goal` and `Done criteria` in
`ai/current-task.md` before starting the work. Never grow scope silently.

If the user chooses to switch, stop and invoke `task-switch`. Do not overwrite
`ai/current-task.md` directly.

If the user chooses future-tasks, append the request to `ai/future-tasks.md`
and continue the current task.

````

Keep the rest of the file unchanged.

- [ ] **Step 2: Update the Rules section of the same file**

Replace the rule line:

```markdown
- Do not silently overwrite an active, review, blocked, or paused task.
```

with:

```markdown
- Do not silently overwrite an active, review, blocked, or paused task.
- Do not extend the current task without updating Goal and Done criteria first.
```

- [ ] **Step 3: Mirror and verify**

```bash
cp ai/skills/task-intake/SKILL.md template/ai/skills/task-intake/SKILL.md
cmp ai/skills/task-intake/SKILL.md template/ai/skills/task-intake/SKILL.md && echo MIRROR_OK
```

Expected: `MIRROR_OK`.

- [ ] **Step 4: Commit**

```bash
git add template/ai/skills/task-intake/SKILL.md
git commit -m "feat: default new requests to different task in task-intake"
```

### Task 3: Align task-switch with the same model

**Files:**

- Modify: `ai/skills/task-switch/SKILL.md`
- Modify: `template/ai/skills/task-switch/SKILL.md`

- [ ] **Step 1: Replace the "How to decide" section**

Replace the section from `## How to decide whether this is a different task` up to, not including, `## Examples`:

```markdown
## How to decide whether this is a different task

A new request is a different task by default.

It is the same task ONLY if it fits the recorded Done criteria of the current
task: it directly advances them, fixes or adjusts work just produced for this
task, runs tests, checks, or review of this same work, or answers the agent's
question.

If the request needs a new Done criterion, it is a different task, even if it
touches the same files or the same UI.

Small iterations stay in the same task only while they serve the recorded
Done criteria. If a request needs a new Done criterion, use the three-option
question from `task-intake` instead of deciding silently.

If unsure, do not guess. Ask the user:

"Похоже, это новая задача, а текущая ещё не закрыта. Переключаемся или продолжаем текущую?"

```

- [ ] **Step 2: Update the "Same task" examples**

Replace:

```markdown
Same task:

- Current task: "Add onboarding screen"; new request: "Make the first step clearer".
- Current task: "Fix login crash"; new request: "Run the failing login test again".
- Current task: "Review payment diff"; new request: "Check the same diff for security risks".
```

with:

```markdown
Same task (fits the recorded Done criteria):

- Current task: "Add onboarding screen"; new request: "Make the first step clearer".
- Current task: "Fix login crash"; new request: "Run the failing login test again".
- Current task: "Review payment diff"; new request: "Check the same diff for security risks".

Different task even though it looks close:

- Current task: "Add onboarding screen"; new request: "Also add a settings screen" — needs a new Done criterion.
- Current task: "Fix login crash"; new request: "Improve login screen layout" — does not advance the recorded Done criteria.
```

- [ ] **Step 3: Remove the now-duplicated UI-iteration sentence**

Delete this paragraph from the old section if it survived Step 1 (it must not appear twice):

```markdown
Small UI iterations can stay in the same task if they clarify the same UI goal. If they create a new deliverable or change Done criteria, check whether `task-switch` is needed.
```

- [ ] **Step 4: Mirror, verify, commit**

```bash
cp ai/skills/task-switch/SKILL.md template/ai/skills/task-switch/SKILL.md
cmp ai/skills/task-switch/SKILL.md template/ai/skills/task-switch/SKILL.md && echo MIRROR_OK
git add template/ai/skills/task-switch/SKILL.md
git commit -m "feat: align task-switch with Done-criteria boundary"
```

### Task 4: Register the rule in architecture.md

**Files:**

- Modify: `ai/architecture.md`
- Modify: `template/ai/architecture.md`

- [ ] **Step 1: Bump the version**

Replace `Version: 6.10` with `Version: 6.11`.

- [ ] **Step 2: Add the Task boundary section**

Insert after the `### On-demand start screen` section (after its last paragraph, before the next `##`/`###` heading):

```markdown
### Task boundary

The recorded Done criteria in `ai/current-task.md` define the task boundary. A new request is a different task by default; it continues the current task only if it fits the recorded Done criteria. Extending the boundary requires user confirmation and a written update of `Goal` and `Done criteria` before work starts. Details live in `task-intake` and `task-switch`.
```

- [ ] **Step 3: Mirror, verify, commit**

```bash
cp ai/architecture.md template/ai/architecture.md
cmp ai/architecture.md template/ai/architecture.md && echo MIRROR_OK
git add template/ai/architecture.md
git commit -m "docs: register task boundary rule (v6.11)"
```

### Task 5: Full verification

- [ ] **Step 1: Automated checks**

```bash
bash scripts/smoke-test.sh
bash scripts/check-consistency.sh
git diff --check HEAD~4..HEAD
```

Expected: `Smoke tests passed.`, `All canonical lists are consistent.`, no whitespace errors.

- [ ] **Step 2: All mirrors**

```bash
for p in AGENTS.md CLAUDE.md ai/architecture.md ai/skills/task-intake/SKILL.md ai/skills/task-switch/SKILL.md; do cmp "$p" "template/$p" && echo "MIRROR_OK $p"; done
```

Expected: five `MIRROR_OK` lines.

- [ ] **Step 3: Entry-file budget recheck**

```bash
wc -l -c AGENTS.md CLAUDE.md
```

Expected: 99 lines each; ≤ 4397 / ≤ 4405 bytes.

- [ ] **Step 4: Manual scenario (fresh session after merge)**

Prompt: mid-task, ask for something outside the recorded Done criteria.
Expected: the agent asks the three-option question and does no work until answered.

- [ ] **Step 5: Update task memory**

Through the active `architecture-update` workflow set `ai/current-task.md` to `Stage: review` and record checks, remaining risks, and the `task-finish` proposal. Do not mark the task done.
