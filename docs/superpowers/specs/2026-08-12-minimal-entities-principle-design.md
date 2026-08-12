# Minimal Entities Principle — Design

## Goal

Make simplicity and controllability a mandatory principle across technical,
work, and personal projects. The architecture should discourage adding any new
entity unless it solves a specific problem and its benefit justifies the extra
complexity.

An entity may be code, a file, dependency, service, process, project,
subscription, medication, or anything else that the user must understand,
monitor, maintain, or manage.

## Placement

- Add one short mandatory rule to `AGENTS.md` and `CLAUDE.md` with identical
  meaning.
- Add one detailed explanation to `ai/architecture.md`.
- Do not create a separate skill or checklist file.
- Update user-facing documentation only where it reproduces the core rules.

This keeps the principle visible in every session while loading its detailed
interpretation only when needed.

## Mandatory Rule

```text
Prefer the simplest sufficient solution. Do not add a new entity—code, file,
dependency, service, process, project, medication, or anything else—unless it
solves a specific problem that existing entities cannot adequately solve and
its benefit justifies the added complexity.
```

## Decision Test

Before proposing or adding a new entity, the agent should:

1. State the specific problem it solves.
2. Check whether an existing entity can solve the problem adequately.
3. Compare the expected benefit with the additional burden of understanding,
   monitoring, maintaining, and managing it.
4. Prefer the simplest option that is sufficient, safe, and complete.

Minimalism does not mean refusing necessary complexity. An entity is justified
when it is required for safety, correctness, legal compliance, or the user's
confirmed goal and no simpler adequate option exists.

For medical and veterinary matters, the principle must not be used to cancel,
replace, or alter a professional prescription. The agent may question or
explain unnecessary additions, but must direct treatment changes back to the
qualified professional.

## Scope And Non-goals

This change adds a decision principle, not a new workflow. It does not:

- create a scoring system;
- require a formal review for trivial additions;
- prohibit multiple entities when they are genuinely necessary;
- create a new skill, service, dependency, or project file beyond this design
  record.

## Verification

- Confirm `AGENTS.md` and `CLAUDE.md` remain equal in meaning.
- Confirm the short and detailed formulations do not contradict each other.
- Run `bash scripts/check-consistency.sh`, `bash scripts/smoke-test.sh`, and
  `git diff --check` after implementation.
- Verify the installer and updater include the changed protected files through
  their existing update mechanism.

## Token Impact

One short rule is always loaded from the entry file. The detailed explanation
is loaded only when `ai/architecture.md` is relevant. No new always-loaded file
or skill is introduced.

## Communication And Epistemic Standards

The same update should consolidate the entry-point communication rules instead
of merely appending more instructions. Preserve these requirements in a compact
form:

- Use a concise, direct, informational style. Add structure only when it
  improves clarity; avoid filler and unnecessary detail.
- Separate verified facts from interpretations, hypotheses, and opinions. Use
  evidence appropriate to the claim, state uncertainty honestly, and never
  invent facts, statistics, sources, or confidence.
- When the user makes an assumption or decision, test its logic and point out
  material errors, missing considerations, counterarguments, and simpler
  alternatives. Prioritize accuracy and clarity over agreement; do not argue
  without a practical reason.
- For medical or veterinary information, use current evidence-based
  professional sources, communicate uncertainty and limits, and do not
  independently replace or cancel a qualified professional's prescription.

These rules must not require citations for statements that are directly
verified through project files, tests, logs, or other primary evidence. They
must not force headings into short answers or require exhaustive answers when a
short one is sufficient.

During implementation, review existing entry-point rules for overlap and
replace redundant wording where possible. The result should remain compact and
must not create a separate communication skill.

## Entry-point Simplification

Refactor `AGENTS.md` and `CLAUDE.md` as compact routing files rather than full
catalogs. Preserve mandatory safeguards and remove repeated explanations.

Keep in the entry files:

- concise core principles;
- protected-file and controlled-memory boundaries;
- session and task lifecycle;
- a compact but complete mandatory routing map;
- rule precedence;
- concise before/after editing requirements.

Move procedural detail and optional tool names to the relevant skills. In
particular, the entry files should not enumerate individual UI-polish tools.
Remove duplicate explanations of Superpowers, task completion, and adjacent UI
test cases. Do not remove a rule merely to meet a line-count target; brevity is
subordinate to safety and unambiguous routing.

The target is approximately 55–70 lines, but semantic completeness is the
acceptance criterion.

## Skill Routing

The generic instruction to open relevant rules is insufficient by itself. The
entry files must say that routing is based on the user's request and each
skill's `name` and `description`, then provide the mandatory routes:

- session start or restored context → `environment-check`;
- new work → `task-intake`; changed unfinished work → `task-switch`;
- bug, regression, crash, performance issue, or complex task → Superpowers;
- tests → `write-tests`;
- UI change → `ui-review`;
- security-sensitive change → `security-review`;
- wording or copy review → `copy-review`;
- release or merge → `release-check`;
- architecture change → `architecture-update`;
- completion → `task-finish`.

Optional implementation tools remain discoverable through the selected skill
and should not occupy the always-loaded context.
