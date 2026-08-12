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
