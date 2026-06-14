---
name: bugfix-workflow
type: worker
description: |
  Use when fixing a bug, regression, crash, performance problem, broken screen, broken state, flaky behavior, or unexpected behavior.
  This skill uses a diagnose-style loop: feedback loop → reproduce → minimize → hypothesize → instrument → fix → regression test → verification handoff.
  Activates when:
  - user reports something is broken, does not work, returns a wrong result, or behaves unexpectedly
  - user mentions a crash, freeze, lag, regression, flaky behavior, or performance problem
  - user mentions a regression after a previous change
  - user says "diagnose", "debug", "почему не работает", "не должно так быть", "должно было", "лагает", "крашится", or similar
  Does NOT activate for:
  - feature requests
  - broad refactoring
  - new functionality without a prior bug report
---

# Bugfix Workflow

Disciplined diagnosis workflow for hard bugs and performance regressions.

Source of inspiration: Matt Pocock's `diagnose` skill. This project keeps its own architecture and adapts the method to `ai/current-task.md`, `ai/decisions.md`, `ai/changelog.md`, `ai/future-tasks.md`, and `task-finish`.

## Core rule

Do not fix from vibes.

For bugs, crashes, flaky behavior, and performance tasks, do not write a full spec or implementation plan based only on an unverified hypothesis.

First build evidence:

1. Reproduce the issue, or explain why it cannot be reproduced.
2. Capture the observed behavior with a test, log, profiler output, screenshot, CLI command, HTTP script, browser script, or manual reproduction steps.
3. Name the expected behavior.
4. Identify the smallest likely affected area.
5. Check relevant active invariants in `ai/decisions.md` before changing architecture-sensitive code.

If the issue cannot be reproduced, the fix can still be shipped as a mitigation.

The final report must say:

- `Root cause: unproven`
- `Fix status: mitigated`
- what evidence supports the mitigation
- what follow-up would prove or disprove the root cause

During confirmed `task-finish` cleanup, record the mitigation clearly in `ai/changelog.md` when it is notable enough for changelog history.

Non-blocking follow-up investigations, missing test seams, and larger refactors discovered during diagnosis should be proposed for `ai/future-tasks.md`, not implemented inside the bugfix unless the user explicitly expands scope.

## Phase 1 — Build a feedback loop

Create the fastest practical pass/fail signal for the bug.

Prefer, in this order:

1. Failing automated test at the seam that reaches the bug.
2. CLI command with fixture input and expected output.
3. HTTP or API script against a local dev server.
4. Headless browser script for UI bugs.
5. Captured trace, request, payload, or event log replay.
6. Minimal harness that exercises the affected code path.
7. Stress, repeated, seeded, or fuzz loop for flaky behavior.
8. Baseline measurement, profiler output, query plan, or timing harness for performance work.
9. Structured human-in-the-loop reproduction steps if automation is not practical.

The loop should be:

- specific enough to show the reported symptom;
- deterministic when possible;
- fast enough to run repeatedly;
- narrow enough to distinguish the real bug from nearby failures.

If no loop can be built, stop and say so. List what was tried and ask for the missing artifact or access: logs, HAR file, screen recording with timestamps, database snapshot, failing input, environment details, or permission for temporary instrumentation.

## Phase 2 — Reproduce and minimize

Run the feedback loop before changing code.

Confirm:

1. The failure matches the user's reported bug.
2. The failure repeats, or for flaky bugs appears often enough to debug.
3. The exact symptom is captured: error, wrong output, wrong screen state, slow timing, or console/network failure.
4. The reproduction is minimized to the smallest practical scenario.

Do not continue to implementation until the bug is reproduced, unless the task is explicitly a mitigation.

## Phase 3 — Hypothesize

Generate 3–5 ranked hypotheses before testing any single theory.

Each hypothesis must be falsifiable:

```text
If <hypothesis> is the cause, then <specific probe or change> will make the failure disappear, move, or become worse.
```

Discard vague hypotheses that do not predict an observable result.

Share the ranked list with the user when the bug is complex, architecture-sensitive, or domain-heavy. Do not block forever if the user is unavailable; proceed with the best-ranked hypothesis and report the assumption.

## Phase 4 — Instrument

Test hypotheses with targeted probes.

Rules:

1. One probe should test one prediction.
2. Prefer debugger, REPL, profiler, or narrow inspection when available.
3. Use targeted logs only at boundaries that distinguish hypotheses.
4. Never "log everything and grep".
5. Mark temporary logs with a unique prefix, for example `[DEBUG-a4f2]`, so they can be removed reliably.
6. For performance regressions, measure first and optimize second.

Temporary diagnostic code may be committed only when keeping it is intentional and useful for the next step.

If temporary diagnostics remain in main, do not write cleanup history directly. In the verification handoff, report:

- diagnostic code location;
- why it remains;
- when to remove it;
- removal criteria;
- risk if it stays too long.

If task memory is being maintained, add removal criteria to `ai/current-task.md` Done criteria or handoff notes when appropriate. Record the retained diagnostics in `ai/changelog.md` only during confirmed `task-finish` cleanup if the retention is notable. Do not update `ai/paused-tasks.md` unless the agent is running `task-switch`.

Do not use `ai/future-tasks.md` for required TEMP diagnostic removal if the current task cannot safely close without that removal. Use `ai/future-tasks.md` only for non-blocking future improvements or investigations.

## Phase 5 — Fix and regression test

Before fixing, decide whether a correct regression-test seam exists.

A correct seam is one where the test exercises the real bug pattern as it appears in the product, not a too-shallow internal detail.

If a correct seam exists:

1. Convert the minimized reproduction into a failing test.
2. Watch it fail.
3. Apply the smallest clean fix.
4. Watch the test pass.
5. Re-run the original feedback loop against the unminimized scenario.

If no correct seam exists:

1. State that clearly.
2. Explain why available seams would give false confidence.
3. Add the best practical check: integration test, manual checklist, profiler baseline, or reproduction script.
4. Flag the missing seam as possible architecture debt if relevant.
5. Propose a future task for the missing seam if it is useful but outside the current bugfix scope.

## Phase 6 — Verification handoff

Before saying the implementation is ready:

1. Re-run the original reproduction or measurement loop.
2. Re-run the regression test or best practical check.
3. Remove all temporary `[DEBUG-...]` instrumentation unless intentionally kept with a removal record.
4. Delete throwaway scripts, or move useful scripts to a clearly named debug or test location.
5. State the proven root cause, or mark it as unproven.
6. State why the fix is minimal and does not include unrelated refactoring.
7. Mention any missing test seam, fragile area, architecture follow-up, or future task candidate.

Then propose `task-finish` if the task appears complete.

Do not run cleanup yourself. Do not update `ai/changelog.md`, `ai/decisions.md`, `ai/future-tasks.md`, or clear `ai/current-task.md` unless the user confirms `task-finish` cleanup or explicitly asks to save a future task.

## Do not

- Do not rewrite large files.
- Do not change storage unless the bug is storage-related.
- Do not change project invariants.
- Do not mix refactoring with bugfixes unless explicitly asked.
- Do not present an unverified hypothesis as proven root cause.
- Do not leave temporary diagnostics without a removal path.
- Do not create `CONTEXT.md`, `docs/adr/`, or a parallel documentation system unless the project explicitly requires it.
- Do not hide unresolved follow-up work in `ai/paused-tasks.md`; use `ai/future-tasks.md` only for non-blocking future work.
