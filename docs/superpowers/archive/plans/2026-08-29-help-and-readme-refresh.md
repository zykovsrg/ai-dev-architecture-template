# Help and README Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give users a short current overview and a clear Help page for all main architecture mechanics.

**Architecture:** README is the short map of capabilities. Help is the practical page. The `start-screen` skill keeps its internal name but presents Help and recognises plain-language help requests.

**Tech Stack:** Markdown and existing shell consistency checks.

## Global Constraints

- Write short, simple Russian for non-developers.
- Do not promise automatic writes.
- Keep `start-screen` as a compatibility alias.
- Rename the public Help file and update every live reference.
- Include Projects Overview, per-project boards, reviewed Obsidian sync, meeting-note routing, project creation, updates, and confirmations.

---

### Task 1: Replace the public start page with Help

**Files:**
- Rename: `getting-started/getting-started.md` → `getting-started/help.md`
- Modify: `ai/skills/start-screen/SKILL.md`

- [x] Write Help in short Russian with sections: `Что можно сделать`, `Команды`, `Obsidian`, `Встречи`, `Подтверждение`, and `Если нужна помощь`.
- [x] Rename the file and change its visible title to `Помощь`.
- [x] Update `start-screen` wording and triggers: `помощь`, `что умеешь`, and `как работать`.
- [x] Check that no live documentation, installer, or smoke-test reference uses the old page path.

### Task 2: Refresh README

**Files:**
- Modify: `README.md`

- [x] Add a short `Что нового` block for overview boards, review-only Obsidian sync, meeting notes, and safe direct opening of legacy hub projects.
- [x] Replace the old start-screen wording with `Помощь` and link to `getting-started/help.md`.
- [x] Rewrite the skills list as a short user command list, including project selection, tasks, Obsidian, meetings, project creation, updates, and Help.
- [x] Keep installation instructions intact unless their Help link changed.

### Task 3: Verify and save

**Files:**
- Modify: documentation files from Tasks 1–2

- [x] Run `git diff --check`.
- [x] Run `bash scripts/check-consistency.sh` and `bash scripts/smoke-test.sh`.
- [x] Check that no live reference uses the old Help path.
- [x] Commit the documentation update.
