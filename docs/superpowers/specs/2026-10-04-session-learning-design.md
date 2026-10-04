# Session learning

Task: TASK-ai-dev-architecture-20261004-001

## User requirements

The Hub learns from both the user's corrections and preferences and the
agent's own repeated mistakes and fixes. Cheap models do the routine work in
both Claude Code and Codex. Learning must not depend on one agent's reminder:
the day plan reports when the last scan ran and offers a fresh one, and the
scan can also be started by hand from either tool. Every session may be read;
rule text never carries personal details. The weekly review shows which rules
were added, changed, promoted to global or merged since the previous weekly
review (several weeks if reviews were skipped).

## Approach

Read the transcripts both tools already store locally instead of recording
every tool call with hooks (the ECC continuous-learning approach). Transcripts
contain the same tool activity plus the user's own messages, need nothing to
run during work, and are readable by either tool as ordinary files. One shared
ledger prevents double counting whichever tool runs the scan. Models only
extract cases; deterministic scripts count, score, promote and render.

Rejected: ECC hook observation (Claude-only in practice: the Codex bundle
ships only a SessionStart hook; records file contents; runs continuously and
writes rules without review). Session-start hook injection (two different
mechanisms, Codex needs separate trust). Per-project catalogs (a cross-project
pattern would need a merge step; one Hub catalog makes promotion a count).

## Components

All parts belong to the existing optional `learning` module.

1. **Collector script** (`scripts/session_collect.py`). Finds transcripts in
   `~/.claude/projects/*/*.jsonl` and `~/.codex/sessions/YYYY/MM/DD/*.jsonl`,
   keeps only sessions whose working directory is inside the Hub root,
   normalizes both formats into one compact text form (user messages,
   assistant replies, tool names with short inputs and error outputs; long
   tool output is cut), and returns sessions not yet in the ledger. The
   session that is still running is skipped and taken by the next scan.
2. **Scan skill** (`hub-session-scan`). Gives the cheap model batches of 10
   normalized sessions plus the catalog rules relevant to the session's
   project and topic. Claude Code uses Claude Haiku 4.5; Codex uses
   GPT-6-Luna. The model returns cases only.
3. **Rule catalog** (`ai/learning/rules.json`, Hub level). Rules with stable
   IDs (`R-<n>`), one-sentence neutral text, kind (`preference` or
   `agent-habit`), cases, computed confidence, scope, status and merge
   history.
4. **Scoring script** (`scripts/session_rules.py`). Validates model output,
   appends cases, computes confidence and scope, applies merges, and renders
   injection files.
5. **Weekly consolidation.** Claude Opus 5.5 or GPT-6.1-Sol proposes
   duplicate merges and checks global rules; the scoring script applies the
   merges; the weekly review shows the report.
6. **Ledger** (`ai/learning/scan-ledger.json`). Cutover date, processed
   session IDs per tool, last scan time, last weekly review date.

## Case format

Each case returned by the model has: rule (`R-<n>` from the supplied list or
`new` with proposed one-sentence text and kind), effect (`confirm`,
`contradict` or `explicit`), project ID, tool, session ID, date, and a
neutral one-sentence description. Project ID is the registry project whose
path contains the session's working directory; for a session at the Hub root
it is the project confirmed inside that session, otherwise `hub`. The script
rejects a case with an unknown rule ID, unregistered project, session ID not
in the batch, or text that looks like a quote of personal data (names,
diagnoses, amounts, contacts). A rejected batch leaves its sessions unprocessed.

## Confidence and scope

Count distinct sessions per rule (repeats inside one session count once):

| Distinct sessions | Base confidence |
|---|---|
| 1–2 | 0.3 |
| 3–5 | 0.5 |
| 6–10 | 0.7 |
| 11+ | 0.85 |

An `explicit` case (the user says to always do something) sets confidence to
at least 0.7 immediately. Each `contradict` case subtracts 0.1. After four
weeks without a confirming case, subtract 0.02 per further week. Confidence
never goes below 0 or above 0.9.

Scope: a rule is project-scoped while all cases come from one project. It
becomes global when cases come from two or more projects and confidence is at
least 0.7. An explicit instruction that is clearly general ("always write
plain Russian") is global at once; when unclear it stays project-scoped.

## Injection

- `ai/learned-rules.md` (Hub level): global rules with confidence ≥ 0.7,
  at most 10, highest first. Root `CLAUDE.md` and `AGENTS.md` reference it.
- `ai/learned-rules/<project-id>.md` (Hub level): that project's rules with
  confidence ≥ 0.7. Read only after the project is confirmed. Files stay in
  the Hub so no scan writes into project folders.

A rule that falls below 0.7 stops being injected; it stays in the catalog.
Removing a rule from the catalog needs the user's explicit yes.

## Flows

**Day plan.** Adds one line after the required sections: date of the last
scan and the number of new sessions in each tool, with an offer to run the
scan. The day-plan validator is updated for that line.

**Scan.** Collector → batches → cheap model → validation → catalog → scoring
→ injection files → commit in the Hub. Work already saved stays saved if the
scan stops halfway.

**Task closure.** `hub-session-review` stays as is; its findings are also
written to the catalog as cases.

**Workflow observations.** `ai/workflow-observations.md` stays as an
append-only input; new entries become cases. Its separate three-repeat
maturity rule is replaced by the catalog formula.

**Weekly review.** Shows rules added, changed, promoted or merged since the
last weekly review date in the ledger, then updates that date. The user can
undo a merge.

## First run

The cutover date is the first scan day. Sessions before it are recorded as
`before-cutover` and are not scanned or counted as new. They can be scanned
later on explicit request.

## Hub boundary exception

The Hub normally reads nothing outside `<hub>/projects`. This feature needs a
narrow, read-only exception approved by the user: the two transcript
directories above, only sessions whose working directory is inside the Hub.
`ai/architecture.md` must state it.

## Testing

Deterministic, no model calls:
- both transcript formats parse correctly from fixture samples;
- a processed session is never counted twice, including scans from both tools;
- the confidence table, `explicit`, `contradict` and decay give the stated
  numbers;
- one-project rules stay project-scoped; two-project rules at ≥ 0.7 become
  global;
- invalid or personal-data cases are rejected and their sessions stay
  unprocessed;
- the global injection file holds at most 10 rules, all ≥ 0.7.

Live:
- scan the cutover-day sessions in Claude Code with Haiku 4.5, then in Codex
  with GPT-6-Luna; the second run reports no new sessions;
- the day's corrections (plain Russian terms, Cyrillic service names) appear
  as rules.

## Open points for the plan

- How each tool starts its cheap model from a skill (Claude subagent with the
  Haiku model; Codex agent role or `codex exec --model gpt-6-luna`) must be
  verified before implementation.
- Exact Claude and Codex transcript fields for working directory and session
  ID are confirmed from real files during implementation.
