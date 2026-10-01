# Session review

Review ID: 2026-10-01-legacy-project-cleanup-closure
Project ID: ai-dev-architecture
Task ID: TASK-ai-dev-architecture-20261001-001
Session ID: unavailable
Trigger: task-close
Coverage: complete
Evidence range: whole visible session from "открой проект: ии-архитектура" to "закрывай"
Missing evidence: none
Chronology audit: every available message reviewed
Claim action audit: "пилот почищен" — preceded by commit and registry check; "удалил 32 проекта, всё в git" — preceded by the second loop output and a status check showing no uncommitted legacy paths; "в seo-content-creator точные копии" — preceded by diff -rq against reference copies; "ai/architecture.md удалил по своему решению" — honest correction after the user's question.
Prior review audit: indexed 2026-09-27..2026-09-28 closures; F1 here is a new mechanism (shell word splitting); F2 shares the root of 2026-09-27-split-architecture-stage-7 F1 (acting beyond what was checked) only loosely, not counted as recurrence.
Result: issues-found
Supplements: none

## Goal and result

Goal: remove legacy standalone architecture copies from hub projects without
losing project-specific work. Outcome: 17 generic skills and
`ai/external-tools.md` removed from 33 projects (external-tools kept where project skills remain) and committed; pointer
entries kept; project-specific skills and `.claude/` kept; registry check passes.
FT-20260812-001 and FT-20260813-001 closed as already done.

## Findings

### F1
Observation: The first batch loop removed no skills because `for s in $G` does not word-split in zsh; it still committed pointer files and printed "ok" for every project.
Evidence: loop output listing all 17 skills as "kept"; a manual check in bot-protection; the rerun with an inline list removed them.
Cause: observed
Root cause: bash idiom used in a zsh shell, and the success message did not verify the intended effect.
Impact: Low. Caught before reporting to the user; one extra commit per project.

### F2
Observation: In the pilot the assistant deleted the pointer `ai/architecture.md` without first checking whether recent hub work intended it; the user had to ask.
Evidence: user question "ссылка на хаб не нужна?"; later check found the hub template `registered-project-architecture.md` from 2026-09-09.
Cause: observed
Root cause: classifying a file as legacy by its path instead of checking current hub templates first.
Impact: Low; restored from the template in the same session.

## Improvement proposals

### P1
Finding: F1
Scope: bulk file operations across hub projects run from this project.
Change: before bulk deletion, compare each target with current hub templates, and after the loop verify the effect (remaining files) rather than trusting "ok"; in zsh write lists inline or use `${=VAR}`.
Rationale: both slips came from not verifying against the real state.
Acceptance test: the next bulk cleanup reports a post-check of remaining files.
Recovery: drop the practice.
Disposition: accepted

## Follow-up

- FT-20261001-001 (design module) deferred by the user.
