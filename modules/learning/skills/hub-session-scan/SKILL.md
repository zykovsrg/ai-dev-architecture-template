---
name: hub-session-scan
description: Scan new Claude Code and Codex sessions into the Hub learning catalog with a cheap model, or run the weekly merge pass.
---

# Hub Session Scan

Module rules: `ai/rules/learning.md`. Runs in Claude Code or Codex; both read
the same transcript folders and the same ledger, so either may run it.

Role instructions live in `ai/skills/hub-session-scan/resources/scanner.md` and
`consolidator.md` (single source for both tools).

## Scan

Transcript text goes only to the batch folder outside the Hub,
`<tmp>` = `${TMPDIR:-/tmp}/hub-session-scan/` (the `batch` command prints its
absolute paths). The Hub folder `ai/tmp/learning/` holds only the rules list,
the cases and the merges (no transcript text).

1. `python3 scripts/session_collect.py --hub <hub> status`. If `cutover` is
   null, run `init --cutover <today>` first (first run scans only today).
   Then list open tasks for the morning task check:
   `python3 scripts/open_task_check.py --hub <hub> --dir <tmp> list`. It
   writes `<tmp>/open-tasks.json` (open current tasks of active projects with
   their Done criteria) and resets `<tmp>/task-checks.json`. A task whose
   `ai/current-task.md` changed today is today's work and is skipped.
2. Repeat until both pending counts are 0:
   a. `python3 scripts/session_collect.py --hub <hub> batch` (add
      `--skip <tool>:<id>` for every session that failed earlier in this run).
      It writes at most 10 sessions and at most 60,000 characters: one
      plain-text file per session in `<tmp>` plus `<tmp>/index.json`, and
      prints `written`, `remaining`, `index` and `files`. If `written` is 0,
      stop the loop: only this run's failed sessions are left.
   b. For each distinct `project` in the index, plus `hub`, run
      `python3 scripts/session_rules.py --hub <hub> relevant --project <id>`.
      Concatenate the outputs, keep only the first entry for each `id`, and
      write them as one JSON array of `{"id", "text", "kind"}` to
      `<hub>/ai/tmp/learning/rules.json`.
   c. Run the scanner; do not do the extraction yourself. The prompt starts
      with the literal line `[hub-session-scan]`, then gives the absolute
      paths of `<tmp>/index.json`, every session file from `files`,
      `<hub>/ai/tmp/learning/rules.json`, `<tmp>/open-tasks.json` when `list`
      found open tasks, and the output `<hub>/ai/tmp/learning/cases.json`.
      - Claude Code: start the `hub-session-scanner` subagent (Haiku) with that
        prompt. Then confirm the model actually used:
        `python3 scripts/session_scan_model.py --agent-id <agentId>` with the
        agentId from the subagent result. It reads only the model field of
        that subagent's transcript. On exit 1 (other model, no transcript or
        no model recorded) stop the scan before applying this batch and tell
        the user. Never ask the model for its name.
      - Codex: run as a subprocess, with `<codex>` = `codex` on PATH, else
        `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`:
        `<codex> exec -m gpt-6-luna -c model_reasoning_effort=low -s read-only --skip-git-repo-check --ephemeral -C <hub> -o <hub>/ai/tmp/learning/cases.json "<prompt>" </dev/null`
        `<prompt>` is: the line `[hub-session-scan]`, then the contents of
        `ai/skills/hub-session-scan/resources/scanner.md`, then the paths
        above, then "Reply with only the JSON." The read-only sandbox
        may read `<tmp>`; it writes nothing itself (`-o` saves the reply).
   d. `python3 scripts/session_rules.py --hub <hub> apply --batch <tmp>/index.json --cases <hub>/ai/tmp/learning/cases.json`.
      New rules that repeat `CLAUDE.md` or `AGENTS.md` are dropped and listed
      in `skipped_standing`; repeats of moved rules come back as `leaks`
      (see `ai/rules/learning.md` § Rule home). Mention both in the report
      under «Новые правила».
      On `ERROR`, give the error back to the scanner once and apply again.
      If it fails again, run each session of this batch alone
      (`batch --session <tool>:<id>`, then steps b–d without a second retry).
      A session that still fails stays pending: note its `<tool>:<id>`, skip
      it for the rest of this run, and report it.
   e. When open tasks exist, keep this batch's task evidence:
      `python3 scripts/open_task_check.py --hub <hub> --dir <tmp> record --batch <tmp>/index.json --cases <hub>/ai/tmp/learning/cases.json`.
      It keeps only met criteria that cite a session of this batch.
3. Morning task check. `python3 scripts/open_task_check.py --hub <hub> --dir <tmp> decide`
   gives one decision per open task:
   - `close` (every Done criterion met with cited evidence) → close the task
     through `hub-task-finish` for that project; the cited criteria and
     sessions are its verification. A future calendar event to delete still
     waits for the user's yes.
   - `pause` → `python3 scripts/open_task_check.py --hub <hub> --dir <tmp> pause --project <id> --task-id <task-id>`;
     it moves the task to `ai/paused-tasks.md` with its `Due:` and schedule
     lines and empties `ai/current-task.md`. Then run the `after-task-write`
     event for that project.
   Append one short entry to the project's `ai/changelog.md` only when the
   decision's `notes` name something important (for a closed task,
   `hub-task-finish` writes it); otherwise write nothing. Write it in your
   own neutral words, never transcript text. No evidence never closes a
   task, and calendar events never prove completion. Pausing is correct
   even for a task worked on yesterday: the day closes, the next morning
   starts clean.
4. Commit `ai/learning/`, `ai/learned-rules.md` and `ai/learned-rules/` in the
   Hub repository. Report in plain Russian as one short opening line
   (result saved) and then exactly these six bold-labelled bullets, each
   one or two short sentences (format approved by the user 2026-10-05,
   task bullet added 2026-10-07):
   - **Разобрано:** real sessions per tool («Клод», «Кодекс») and, apart
     from them, journal lines and review files; failed session IDs that
     stay pending, or that none failed and the queue is empty.
   - **Новые правила: N.** Then one sub-line per new rule:
     `<project or «общее»> — <what the rule asks, in plain Russian>`. Use
     the project's Russian name; Hub-level rules are «общее». No rule IDs
     or raw English rule text (user decision 2026-10-08).
   - **Подключены к работе:** which new rules are now injected; name any
     that stay only in the catalog and why (for example the global limit).
   - **Стали общими: N.** Then one sub-line per rule that became global,
     in the same `<was project or «общее»> — <what the rule asks>` form, or
     «нет».
   - **Модель:** the model confirmed by `session_scan_model.py` for every
     scanner run (Claude Code), or the `-m` model passed to Codex.
   - **Задачи:** per project with an open task: closed (закрыта), paused
     (на паузе) or unchanged (не тронута: изменена сегодня), or «открытых
     задач нет».
   Optionally add one plain line after the bullets for a notable
   observation (for example, duplicates worth merging at the weekly pass).

## Weekly pass

Run from the weekly review. Run the consolidator with the catalog
`ai/learning/rules.json`:
- Claude Code: `hub-learning-consolidator` subagent (Opus); the task prompt
  starts with `[hub-session-scan]`; output `<hub>/ai/tmp/learning/merges.json`.
  Confirm the model from the subagent result.
- Codex: same subprocess shape as the scanner with `-m gpt-6.1-sol`, the
  contents of `consolidator.md`, and `-o <hub>/ai/tmp/learning/merges.json`.

For each merge proposal run `session_rules.py merge`; list `check` items for
the user. To remove a catalog rule (`retire_rule`), ask the user and only after
an explicit yes run `python3 scripts/session_rules.py --hub <hub> retire --rule R-n`;
the rule stays in the catalog with status `retired` and a `retired` history
event. Then `session_rules.py report` and show its events. After the review,
`session_rules.py weekly-done --date <today>`.

## Boundaries

Reads only the two transcript folders named in `ai/architecture.md`, and only
sessions inside the Hub. The morning task check reads and writes project task
files only as `### Morning task check exception` in `ai/architecture.md` allows. Never copies transcript text into Hub files: session
text goes only to `<tmp>` outside the Hub; only the catalog's neutral
sentences are stored. Removing (retiring) a rule needs the user's explicit yes.
