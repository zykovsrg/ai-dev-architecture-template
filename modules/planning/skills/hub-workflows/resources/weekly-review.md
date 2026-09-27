# weekly-review

This resource defines only the `weekly-review` scenario. The core `SKILL.md` remains authoritative for scope, security, canonical-source rules, proposal envelopes, confirmation, and learning lifecycle. Nothing here widens those permissions.

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

For learning, render active numeric goal pace/forecast and read the observation journal. Group repeated friction/calendar drift and offer `promote_rule` after three repeats or two in one week; offer `retire_rule` for contradicted or excess rules. Before either rule-change proposal run `check-workflow-memory.sh`; failure blocks rule changes only. All learning changes use the core proposal/confirmation contract.
