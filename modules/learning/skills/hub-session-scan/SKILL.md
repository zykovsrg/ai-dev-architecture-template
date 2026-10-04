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
      `<hub>/ai/tmp/learning/rules.json` and the output
      `<hub>/ai/tmp/learning/cases.json`.
      - Claude Code: start the `hub-session-scanner` subagent (Haiku) with that
        prompt. Confirm the model actually used from the subagent result; do
        not ask the model for its name.
      - Codex: run as a subprocess, with `<codex>` = `codex` on PATH, else
        `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`:
        `<codex> exec -m gpt-6-luna -c model_reasoning_effort=low -s read-only --skip-git-repo-check --ephemeral -C <hub> -o <hub>/ai/tmp/learning/cases.json "<prompt>" </dev/null`
        `<prompt>` is: the line `[hub-session-scan]`, then the contents of
        `ai/skills/hub-session-scan/resources/scanner.md`, then the paths
        above, then "Reply with only the JSON array." The read-only sandbox
        may read `<tmp>`; it writes nothing itself (`-o` saves the reply).
   d. `python3 scripts/session_rules.py --hub <hub> apply --batch <tmp>/index.json --cases <hub>/ai/tmp/learning/cases.json`.
      On `ERROR`, give the error back to the scanner once and apply again.
      If it fails again, run each session of this batch alone
      (`batch --session <tool>:<id>`, then steps b–d without a second retry).
      A session that still fails stays pending: note its `<tool>:<id>`, skip
      it for the rest of this run, and report it.
3. Commit `ai/learning/`, `ai/learned-rules.md` and `ai/learned-rules/` in the
   Hub repository. Report in plain Russian: sessions scanned per tool, new
   rules, rules now injected, rules that became global, and the IDs of
   sessions that failed and stay pending.

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
sessions inside the Hub. Never copies transcript text into Hub files: session
text goes only to `<tmp>` outside the Hub; only the catalog's neutral
sentences are stored. Removing (retiring) a rule needs the user's explicit yes.
