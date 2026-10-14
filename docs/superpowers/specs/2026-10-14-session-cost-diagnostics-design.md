# Session cost diagnostics

Task: TASK-ai-dev-architecture-20261013-001

## User requirements

The user wants to improve the Hub for speed and token economy using evidence
from real sessions. Findings are shown once a week; nothing is fixed
automatically. Every fix goes through the user's yes at the weekly review.

Agreed in the design discussion (2026-10-13/14):

- Count only waste that does not depend on task difficulty: **losses** and
  **startup cost**. Rejected: cost per user message and cost per procedure
  (day plan, scan): tasks differ too much and day-plan sessions mix in other
  work, so comparisons would mislead.
- A deterministic script does all counting. No model reads transcripts for
  this feature.
- At the weekly review the agent reads the small numbers table and writes
  three ranked conclusions: what to fix first and why.
- Dead-code and tech-debt checks of code are out of scope (FT-20261013-001).

## Approach

Verified before design: Claude Code transcripts carry `message.usage` on
assistant records; Codex transcripts carry `event_msg` / `token_count` with
`last_token_usage`. Both already record every tool call and tool error, which
`scripts/session_collect.py` parses today.

Rejected: adding technical findings to the cheap-model scanner. The scanner
sees only the first 200 characters of each tool call and at most 40,000
characters per session (middle cut), so it would miss failures; and counting
is deterministic work a script does exactly and for free.

## Component: `scripts/session_cost.py`

Belongs to the optional `learning` module
(`modules/learning/scripts/session_cost.py` → `scripts/session_cost.py`).

Command: `python3 scripts/session_cost.py --hub <hub> week --until <YYYY-MM-DD>`.
Selects Hub sessions (same discovery and `_inside` check as
`session_collect.py`, reused by import) whose start date falls in the 7 days
ending on `--until`. Independent of the scan ledger. Skips sessions started by
the scanner (`[hub-session-scan]` first message), like the collector.

### Steps and tokens

A **step** is one model call.
- Claude: assistant records grouped by `message.id` (one call is split over
  several records with the same usage; count it once). Main session files
  only (`*/*.jsonl`); subagent transcripts are out of scope for v1.
- Codex: each `token_count` event's `last_token_usage` belongs to the tool
  calls and messages since the previous `token_count` event.

Per step the script keeps three numbers:
- `fresh` — Claude `input_tokens + cache_creation_input_tokens`; Codex
  `input_tokens - cached_input_tokens`;
- `cached` — Claude `cache_read_input_tokens`; Codex `cached_input_tokens`;
- `output` — `output_tokens` (Codex adds `reasoning_output_tokens`).

Cached tokens are reported separately and never summed into `fresh`: they
cost far less, so a single total would overstate waste.

### Losses

Each step falls into at most one category, checked in this order:

1. `error_retry` — steps after a tool error, up to and including the next
   successful call of the same tool.
2. `repeat_command` — a shell call whose command string is identical to an
   earlier one in the same session.
3. `repeat_read` — a read of a file already read in the same session with no
   edit or write to that file in between (Claude `Read` by `file_path`;
   Codex only through identical commands, i.e. category 2).

### Startup

Startup is every step from the session start up to and including the step
that produced the first assistant text shown to the user. It covers loading
Hub rules, skills and routing.

### Labels and privacy

Losses are grouped by a label: tool name plus, for shell calls, the program
name and, when it is a script inside the Hub, its Hub-relative path; for
reads, the Hub-relative path or `outside-hub`. Command arguments, file
contents, message text and outside paths are never stored. Session IDs are
stored (not personal).

### Output

Writes `ai/learning/cost/<YYYY>-W<ww>.json` in the Hub (numbers and labels
only) and prints the same JSON:
- totals for the week: steps, fresh, cached, output; loss share of fresh;
- `losses`: per category, top 10 labels by fresh tokens with counts;
- `startup`: median and top 5 sessions by fresh tokens, with session ID,
  project and date;
- sessions skipped because they had no usage data, with the reason.

## Weekly review change

`modules/planning/skills/hub-workflows/resources/weekly-review.md`, only when
`learning` is listed: run the script, then show `## Технические потери`:
the totals line, the top 5 of each loss category, startup median and top 3,
then three ranked conclusions `- <что чинить> — почему: <цифры> — экономия: <оценка>`.
A fix the user accepts goes to `## Нужны решения` and follows the same
Superpowers flow as mechanism candidates. Without usage data the section says
so in one line.

## Architecture rule change

`ai/architecture.md` § Transcript read exception: add `scripts/session_cost.py`
with the same limits (read-only, Hub sessions only, no transcript text
stored in the Hub). `modules/learning/module.md`: add the install line and
the write `ai/learning/cost/`.

## Errors

- A transcript line that is not JSON is skipped (as in the collector).
- A session without any usage numbers is listed as skipped, never counted
  as zero.
- A missing transcript folder gives an empty week with a note, exit 0.

## Testing

Fixtures (synthetic JSONL, no real text) for both tools covering: one call
split over several records (counted once), an error then a retry, an
identical repeated command, a repeated read with and without an edit in
between, startup ending at the first assistant text, a session without usage,
a session outside the Hub (ignored), a scanner session (ignored), week
boundaries. A test asserts that no argument, outside path or message text
appears in the output. The existing learning test suite must pass.

## Rollout

Change the module source in this project, run the tests, then deploy to the
Hub copy through the existing release flow and run the script once on the
real previous week; report the result to the user.
