# Task 3 Report: Project Routing, Registration, Switching, and Maintenance Skills

## Implementation summary

Added four confirmation-gated hub workflows and structural smoke assertions for
their required safety boundaries. The workflows keep routing reads inside hub
metadata until confirmation, keep a project switch separate from a task switch,
limit registration discovery to direct child directory names, and make registry
maintenance report-only until an individual approval is received.

## Changed files

- `hub-template/ai/skills/project-router/SKILL.md`
- `hub-template/ai/skills/project-switch/SKILL.md`
- `hub-template/ai/skills/project-register/SKILL.md`
- `hub-template/ai/skills/registry-check/SKILL.md`
- `scripts/hub-smoke-test.sh`
- `.superpowers/sdd/task-3-report.md`

## TDD RED/GREEN evidence

### RED

After adding structural and safety assertions to `scripts/hub-smoke-test.sh`
and before creating the skills, this command exited `1`:

```text
bash scripts/hub-smoke-test.sh
```

Observed failure:

```text
FAIL: missing file: .../hub-template/ai/skills/project-router/SKILL.md
```

The failure proves that the new test checks the requested skill file before
any implementation exists.

### GREEN

After implementing the skills and aligning two wrapped phrases with the
structural assertions, the focused verification completed with exit `0`:

```text
bash scripts/hub-smoke-test.sh && bash -n scripts/hub-smoke-test.sh scripts/check-hub-registry.sh
```

## All tests and checks

- `bash scripts/hub-smoke-test.sh` — passed.
- `bash scripts/smoke-test.sh` — passed: `Smoke tests passed.`
- `bash scripts/check-consistency.sh` — passed: `All canonical lists are consistent.`
- `bash -n scripts/hub-smoke-test.sh scripts/check-hub-registry.sh scripts/smoke-test.sh scripts/check-consistency.sh` — passed.
- `git diff --check` — passed.
- Required-phrase scan across all four skills — passed.

## Self-review

- `project-router` reads only compact hub metadata and candidate cards before
  confirmation, including only relevant active cross-project signals, caps
  candidates at three, reports high/medium/low routing confidence, and
  includes all five required Russian response templates.
- `project-switch` displays both projects, warns that unfinished work remains
  unchanged, validates the canonical registered path after confirmation, then
  updates only `active-project` before entering the target project's existing
  environment/task workflow.
- `project-register` cannot recurse or read project content during primary
  inventory, classifies only from direct-child names before individual project
  confirmation, and defers `.git`, context, card, and registry actions to their
  separate approval gates.
- `registry-check` runs the existing validator and reports missing paths,
  stale metadata, direct-child registration gaps, archive candidates, and old
  signals without changing anything; a reminder can offer but cannot run it.
- Permanent workflow instructions are English; all user-facing examples are
  Russian. No hub core architecture, registry data, or project files changed.

## Concerns

No open concerns were found after the reviewer follow-up.

## Reviewer findings follow-up

### RED

The strengthened boundary regression was added to
`scripts/hub-smoke-test.sh` before the corresponding skill changes. The first
run failed as expected:

```text
FAIL: router must allow only relevant hub cross-project signals and forbid project memory/code before confirmation
```

After allowing hub-owned, active signals, the next RED run failed on the
separate template requirement:

```text
FAIL: router multi-candidate template must include confidence for all three candidate slots
```

These failures prove the checks reject the former router behaviour rather than
merely finding broad phrases. The smoke tests also create intentionally unsafe
fixtures: one removes the cross-project-signal allowlist, one removes the third
candidate slot, and one injects an early `.git` instruction into primary
registration inventory. Each fixture must be rejected.

### GREEN

The final fresh verification passed:

```text
bash scripts/hub-smoke-test.sh
bash scripts/smoke-test.sh
bash scripts/check-consistency.sh
bash -n scripts/hub-smoke-test.sh scripts/check-hub-registry.sh scripts/smoke-test.sh scripts/check-consistency.sh
git diff --check
```

The router now permits only relevant active hub cross-project signals before
confirmation and continues to forbid project memory, source code,
configuration, and project files. Its multi-candidate response has three
numbered slots, each with routing confidence. Primary registration inventory
uses only direct-child directory names; `.git` metadata and minimal project
context are deferred until explicit confirmation of the individual child.

### Changed files for reviewer follow-up

- `hub-template/ai/skills/project-router/SKILL.md`
- `hub-template/ai/skills/project-register/SKILL.md`
- `scripts/hub-smoke-test.sh`
- `.superpowers/sdd/task-3-report.md`
