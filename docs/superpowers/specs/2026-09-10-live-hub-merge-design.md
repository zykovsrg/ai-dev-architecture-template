# Live hub merge design

## Purpose

Update the installed hub without discarding its existing task, goal, calendar,
and workflow-learning behavior. Add the completed architecture refactor as a
compatible layer, including low-cost session review at task closure and on
explicit request.

## Rules to preserve

- Goals keep their canonical log, confirmed entries, calculation, and planning
  and review output.
- Workflow learning keeps observations, promoted and retired rules, calendar
  snapshots, friction capture, and the weekly review lifecycle.
- Calendar-linked task changes keep the existing joint preview and one
  confirmation.
- Locally changed managed files are never overwritten by a release operation.

## New rules to add

- A task can close only after its deterministic checks and a saved session
  review pass.
- A selected past session can be reviewed on request.
- Session reviews start with deterministic checks, use Luna for focused review,
  and escalate to Terra only for ambiguity or material risk.
- Review findings are proposals; no rule or workflow changes automatically.
- Shared project entries point to the hub rather than duplicate generic rules.

## Integration approach

The hub template becomes the combined canonical source. Its architecture and
affected workflow skills retain the existing detailed learning and calendar
instructions, then add the new session-review and safe-update rules. Tests
cover the combined contract. The release manifest is rebuilt. The safe release
tool applies only after its preview has no conflicts; existing working files
are then either preserved as identical to the combined template or explicitly
merged before release.

## Success criteria

1. No current goal, task, calendar, or weekly-learning instruction is removed.
2. Task closure invokes the low-cost session review before task memory clears.
3. The working hub receives all new scripts and resources through the safe
   release path, with no conflicts.
4. Unit and installed-hub checks pass after deployment.
