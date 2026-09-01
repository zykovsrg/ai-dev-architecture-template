# Short And Simple Agent Answers — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make agent answers short and plain by replacing soft brevity wording and heavy mandatory report formats with one hard `Output` rule.

**Architecture:** Markdown-only change. A single new `Output` section in the entry files carries a numeric limit plus techniques. The old `Output` section, the old brevity bullet, and the two `Output format ...` sections in `ai/architecture.md` are deleted. Working copy, `template/`, and the hub all get the same rule.

**Tech Stack:** Markdown, Bash verification scripts (`scripts/check-consistency.sh`, `scripts/smoke-test.sh`).

**Spec:** `docs/superpowers/specs/2026-09-01-short-simple-answers-design.md`

## Global Constraints

- Persistent AI-facing instructions are written in English.
- `AGENTS.md` and `CLAUDE.md` are protected architecture files: the change runs under the `architecture-update` workflow with explicit user confirmation before the first edit.
- `AGENTS.md` and `CLAUDE.md` must stay equal in meaning; only tool-specific notes may differ.
- `template/AGENTS.md` and `template/CLAUDE.md` must stay equal in meaning to each other.
- Do not touch the `canon:` marker blocks.
- Keep the `File Classes` line about naming the workflow that allowed a memory change.

## Canonical `Output` section text

Used verbatim in `AGENTS.md`, `CLAUDE.md`, `template/AGENTS.md`, `template/CLAUDE.md`:

```markdown
## Output

- Default answer: at most 5 lines. Go longer only when the user asks, or when comparing options — then give the 5-line answer first and put details below it.
- Answer first, reason second. No preamble about what you analyzed or intend to do.
- Replace technical terms with everyday words. If a term is unavoidable, explain it in brackets at first use.
- Keep internal machinery out of the answer: mode labels, memory file names, workflow names, status fields. Show them only when the user asks.
- One question per message. Lists: at most 5 items.
- Never declare a task closed. Propose `task-finish` and wait for confirmation.
- This holds under any external methodology, including Superpowers.
```

Hub variant (`_ai-hub/CLAUDE.md`) — identical minus the `task-finish` line:

```markdown
## Output

- Default answer: at most 5 lines. Go longer only when the user asks, or when comparing options — then give the 5-line answer first and put details below it.
- Answer first, reason second. No preamble about what you analyzed or intend to do.
- Replace technical terms with everyday words. If a term is unavoidable, explain it in brackets at first use.
- Keep internal machinery out of the answer: mode labels, memory file names, workflow names, status fields. Show them only when the user asks.
- One question per message. Lists: at most 5 items.
- This holds under any external methodology, including Superpowers.
```

## File Structure

- `CLAUDE.md`, `AGENTS.md` — entry files, working copy. Carry the new `Output` section.
- `ai/architecture.md` — detailed rules, working copy. Loses two sections.
- `template/CLAUDE.md`, `template/AGENTS.md`, `template/ai/architecture.md` — same changes, shipped to new projects.
- `/Users/zykovsrg/Documents/vibecode/_ai-hub/CLAUDE.md` — hub entry file, hub variant of the section.

---

### Task 1: Open `architecture-update` and confirm

**Files:**
- Read: `ai/skills/architecture-update/SKILL.md`

**Interfaces:**
- Consumes: nothing.
- Produces: explicit user confirmation to edit protected files; whatever record the skill requires.

- [ ] **Step 1: Read the workflow**

Run: `cat ai/skills/architecture-update/SKILL.md`

- [ ] **Step 2: Follow the skill's confirmation step**

Show the user the exact list of protected files to be changed:
`AGENTS.md`, `CLAUDE.md`, `ai/architecture.md`, `template/AGENTS.md`, `template/CLAUDE.md`, `template/ai/architecture.md`, and the hub's `CLAUDE.md`.
Wait for explicit confirmation. Do not edit before it.

- [ ] **Step 3: Do any record-keeping the skill requires**

If the skill requires an entry in `ai/decisions.md` or `ai/changelog.md`, follow it exactly. Do not invent extra records.

---

### Task 2: Working-copy entry files

**Files:**
- Modify: `CLAUDE.md:24` (delete), `CLAUDE.md:82-84` (replace section)
- Modify: `AGENTS.md:24` (delete), `AGENTS.md:82-84` (replace section)

**Interfaces:**
- Consumes: confirmation from Task 1; the canonical `Output` text above.
- Produces: the new `## Output` section that Task 3 and Task 4 mirror.

- [ ] **Step 1: Delete the old brevity bullet in both files**

Delete this exact line from `CLAUDE.md` and `AGENTS.md` (line 24 in both):

```
- Use a concise, direct, informational style with very simple words. Default to a short answer; give long explanations only when the user asks. This holds for output produced under any external methodology, including Superpowers.
```

Leave the rest of `## Core Principles` untouched.

- [ ] **Step 2: Replace the old `## Output` section in both files**

Delete the whole existing `## Output` section (heading plus its single paragraph, at the end of the file) and put the canonical `## Output` section from this plan in its place. It stays the last section, after `## Precedence`.

- [ ] **Step 3: Verify the two files still match**

Run: `diff <(sed '1,6d' AGENTS.md) <(sed '1,6d' CLAUDE.md)`
Expected: only the tool-specific lines differ (the Codex/Claude Code skill-activation paragraph in `## Lifecycle And Routing`). No difference inside `## Output` or `## Core Principles`.

- [ ] **Step 4: Verify no leftovers**

Run: `grep -n "concise, direct\|state \`Mode\|task memory changed" AGENTS.md CLAUDE.md`
Expected: no output.

- [ ] **Step 5: Commit**

```bash
git add AGENTS.md CLAUDE.md
git commit -m "feat: hard output rule in working-copy entry files

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Working-copy `ai/architecture.md`

**Files:**
- Modify: `ai/architecture.md:584-593` (delete), `ai/architecture.md:614-633` (delete)

**Interfaces:**
- Consumes: the new `Output` section from Task 2, which now covers this ground.
- Produces: an architecture file with no output-format sections.

- [ ] **Step 1: Delete `## Output format before changes`**

Delete from the line `## Output format before changes` up to but not including `## Scope control`. That removes the heading, its three numbered items, and the trailing sentence about listing technical files.

- [ ] **Step 2: Delete `## Output format after changes`**

Delete from the line `## Output format after changes` up to but not including `## Clean architecture principle`. That removes the heading, its six numbered items, and the list of task-memory files.

- [ ] **Step 3: Verify both sections are gone**

Run: `grep -n "Output format" ai/architecture.md`
Expected: no output.

- [ ] **Step 4: Verify nothing else points at them**

Run: `grep -rn "Output format" --include=*.md . | grep -v docs/superpowers`
Expected: only `template/ai/architecture.md` still matches — Task 4 removes it.

- [ ] **Step 5: Commit**

```bash
git add ai/architecture.md
git commit -m "refactor: drop mandatory output-format sections from architecture

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: Template files

**Files:**
- Modify: `template/CLAUDE.md:35` (delete), `template/CLAUDE.md:93-95` (replace section)
- Modify: `template/AGENTS.md:35` (delete), `template/AGENTS.md:93-95` (replace section)
- Modify: `template/ai/architecture.md:572-581` (delete), `template/ai/architecture.md:602-621` (delete)

**Interfaces:**
- Consumes: the canonical `Output` text; the deletions proved in Tasks 2 and 3.
- Produces: template files that new projects install.

- [ ] **Step 1: Apply Task 2's two edits to `template/CLAUDE.md` and `template/AGENTS.md`**

Same deleted bullet, same replacement `## Output` section, verbatim.

- [ ] **Step 2: Apply Task 3's two deletions to `template/ai/architecture.md`**

Same two sections, same boundaries (`## Scope control` and `## Clean architecture principle` are the stop lines).

- [ ] **Step 3: Verify template entry files match each other**

Run: `diff <(sed '1,6d' template/AGENTS.md) <(sed '1,6d' template/CLAUDE.md)`
Expected: only the tool-specific skill-activation lines differ.

- [ ] **Step 4: Verify no leftovers anywhere**

Run: `grep -rn "Output format\|concise, direct" --include=*.md . | grep -v docs/superpowers`
Expected: no output.

- [ ] **Step 5: Run the project checks**

```bash
bash scripts/check-consistency.sh
bash scripts/smoke-test.sh
```
Expected: both pass. If either fails, read the failure and fix it before committing — do not commit a red check.

- [ ] **Step 6: Commit**

```bash
git add template/
git commit -m "feat: hard output rule in template files

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Hub entry file

**Files:**
- Modify: `/Users/zykovsrg/Documents/vibecode/_ai-hub/CLAUDE.md`

**Interfaces:**
- Consumes: the hub variant of the `Output` text above.
- Produces: nothing downstream.

This file lives in a different repository. Commit it separately, from the hub root.

- [ ] **Step 1: Delete the hub's soft brevity bullet**

Delete this exact line from `## Core Principles`:

```
- Use concise Russian, very simple words, and short answers; explain unfamiliar technical terms simply. This holds for output under any external methodology, including Superpowers.
```

- [ ] **Step 2: Add the hub variant `## Output` section**

Append it as the last section of the file, after `## Boundaries`. Use the hub variant from this plan — no `task-finish` line.

- [ ] **Step 3: Keep the Russian-language rule**

The deleted bullet also carried "talk in Russian". Confirm the hub still states it somewhere. If it does not, add this bullet to `## Core Principles`:

```
- Talk to the user in Russian; keep persistent AI-facing instructions in English.
```

- [ ] **Step 4: Verify the hub registry still validates**

Run: `bash scripts/check-hub-registry.sh`
Expected: pass.

- [ ] **Step 5: Commit from the hub root**

```bash
git add CLAUDE.md
git commit -m "feat: hard output rule for the hub entry file

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: Close out

**Files:**
- Modify: `ai/changelog.md` (only if `architecture-update` requires it)

**Interfaces:**
- Consumes: the record-keeping rules read in Task 1.
- Produces: a finished task.

- [ ] **Step 1: Record the change as the workflow requires**

Follow whatever `ai/skills/architecture-update/SKILL.md` said in Task 1. Add nothing beyond it.

- [ ] **Step 2: Show the user the full diff**

Run: `git log --oneline -5` and `git diff --stat HEAD~4`

- [ ] **Step 3: Propose `task-finish`**

Do not close the task. Propose it and wait.
