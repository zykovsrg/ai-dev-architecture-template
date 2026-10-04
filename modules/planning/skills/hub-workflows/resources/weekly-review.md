# weekly-review

This resource defines only the `weekly-review` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, write policy, and learning lifecycle. Nothing here widens those permissions.

Render these blocks in this exact order:

1. `## Архипроекты`
2. one `### <archiproject-id> — <name>` block per scoped primary archiproject
3. optional `#### Детали проектов` immediately after its owning archiproject block
4. `## Три результата недели`
5. `## Нужны решения`

Each archiproject block uses this field order: `- Цель:`, `- Вклад основного проекта:`, `- Срок/прогноз:`, `- Ожидания и follow-up:`, `- Риск:`. Only canonical primary-archiproject membership counts; a related link never implies contribution.

Show `#### Детали проектов` only for a dated risk, blocker, or waiting record. Render detail as `- <project-id> — <risk, blocker, or waiting>; дата: <YYYY-MM-DD>; источник: <canonical-path>`.

Under `## Три результата недели`, render exactly three numbered executable outcomes grounded in canonical records. If a grounded result is unavailable, preserve the slot and write `Недостаточно канонических данных для результата.` Do not invent an outcome.

If `ai/archiprojects.md` is missing or has no scoped archiproject, state that under `## Архипроекты`, omit invented archiproject blocks, still show safe project-level risks, then keep all three result slots.

When the request names an archiproject group, resolve it via `scripts/archiprojects.py tree --hub <hub>` and pass `--group <group-id>` to `scripts/read-compact-task-index.py`, same as the core `SKILL.md` group filter; report an unknown group instead of guessing. This only narrows which projects' task records are read — it never substitutes for project confirmation elsewhere.

Render active numeric goal pace/forecast only when `goals` is listed in `ai/modules.md`.

Only when `learning` is listed in `ai/modules.md`, read the observation journal and run `python3 scripts/calendar_drift.py --hub <hub> summary --until <date>` for calendar repeat candidates (kind, project, count), group repeated friction/calendar drift, then run the `hub-session-scan` weekly pass and show `session_rules.py report`
(since the last weekly review; several weeks if reviews were skipped): rules
added, changed, made global, merged or unmerged, in plain Russian; offer to undo
any merge; offer `retire_rule` only for a catalog rule the user wants removed, and only after the user's explicit yes run `python3 scripts/session_rules.py --hub <hub> retire --rule R-n` (status `retired`, shown in the report). Before either rule-change proposal run `check-workflow-memory.sh`; failure blocks rule changes only. All learning changes use the core proposal/confirmation contract.

Only when `learning` is listed in `ai/modules.md`, also handle open session-review proposals as `ai/rules/learning.md` § Open review proposals defines: oldest first, at most ten per review, and report how many remain.
