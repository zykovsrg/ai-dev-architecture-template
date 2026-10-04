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

1. `python3 scripts/session_collect.py --hub <hub> status`. If `cutover` is
   null, run `init --cutover <today>` first (first run scans only today).
2. Loop while `pending` is not zero:
   a. `python3 scripts/session_collect.py --hub <hub> batch --limit 10 --out ai/tmp/learning/batch.json`
   b. For the projects in the batch, `python3 scripts/session_rules.py --hub <hub> relevant --project <id>`;
      merge the lists into `ai/tmp/learning/rules.json`.
   c. Run the scanner; do not do the extraction yourself.
      - Claude Code: start the `hub-session-scanner` subagent (Haiku). Its task
        prompt must start with the line `[hub-session-scan]`, then give the
        batch path, the rules path and the output path
        `ai/tmp/learning/cases.json`. Confirm the model actually used from the
        subagent result; do not ask the model for its name.
      - Codex: run as a subprocess, with `<codex>` = `codex` on PATH, else
        `/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex`:
        `<codex> exec -m gpt-6-luna -c model_reasoning_effort=low -s read-only --skip-git-repo-check --ephemeral -C <hub> -o ai/tmp/learning/cases.json "<prompt>" </dev/null`
        `<prompt>` is: the literal first line `[hub-session-scan]`, then the
        contents of `ai/skills/hub-session-scan/resources/scanner.md`, then the
        batch and rules file paths, then "Reply with only the JSON array."
   d. `python3 scripts/session_rules.py --hub <hub> apply --batch ai/tmp/learning/batch.json --cases ai/tmp/learning/cases.json`.
      On `ERROR`, give the error back to the role once and retry; if it
      fails again, stop the loop and report. Unapplied sessions stay pending.
3. Commit `ai/learning/`, `ai/learned-rules.md` and `ai/learned-rules/` in the
   Hub repository. Report in plain Russian: sessions scanned per tool, new
   rules, rules now injected, rules that became global.

## Weekly pass

Run from the weekly review. Run the consolidator with the catalog
`ai/learning/rules.json`:
- Claude Code: `hub-learning-consolidator` subagent (Opus); the task prompt
  starts with `[hub-session-scan]`; output `ai/tmp/learning/merges.json`.
  Confirm the model from the subagent result.
- Codex: same subprocess shape as the scanner with `-m gpt-6.1-sol`, the
  contents of `consolidator.md`, and `-o ai/tmp/learning/merges.json`.

For each merge proposal run `session_rules.py merge`; list `check` items for
the user. Then `session_rules.py report` and show its events. After the
review, `session_rules.py weekly-done --date <today>`.

## Boundaries

Reads only the two transcript folders named in `ai/architecture.md`, and only
sessions inside the Hub. Never copies transcript text into Hub files; only
the catalog's neutral sentences are stored. Removing a rule needs the user's
explicit yes.
