# Handoff — smoke-test drift, 2026-09-10

## Status

The day-editing-loop work is finished and committed on branch
`day-editing-loop`, and both skills are synced into the installed hub. What
remains is unrelated repair work discovered along the way.

## The problem

`scripts/hub-smoke-test.sh` asserts on exact phrases from the skill files.
Several skills were reworded in earlier commits without updating those phrases,
so the suite fails on stale text while the rules themselves are intact. The
suite fails fast, so each repair reveals the next one.

Verified: the suite already failed at `eeac361`, before this branch started.

## Repaired so far

- `hub_workflows_skill_contract_valid` — rewritten for the new day-editing
  rules, plus three assertions that could never match (bullet order, "every"
  vs "each" entry, capitalized "Do not report") and one rejection fixture that
  deleted by a phrase broken across lines (commit `ae295ce`).
- `project_create_contract_valid` — expected "active-project.md only after
  successful validation"; the skill has said "Only after successful validation
  ... update `ai/active-project.md`" since `61ba7aa` (commit `fba19ab`).

## Next failure

`hub_task_finish_knowledge_offer_valid` at `scripts/hub-smoke-test.sh:419-427`.
Three of its four phrases drifted; the rule in
`hub-template/ai/skills/hub-task-finish/SKILL.md:39-41` is intact.

| Assertion expects | Skill actually says |
|---|---|
| `After the normal completion check` | `After the review, if durable records ...` |
| `may offer the hub-owned \`hub-knowledge-review\`` | `may offer \`hub-knowledge-review\`` |
| `Declining the offer has no effect on task closure` | `Declining it has no effect on closure` |

`never start it automatically` still matches.

## How to continue

Run `bash scripts/hub-smoke-test.sh`, take the named failure, compare the
assertion phrases against the skill file, and update the assertion to the
current wording without weakening its meaning. Repeat until the suite passes.
Never change a skill rule to satisfy a test; the tests are what drifted.
