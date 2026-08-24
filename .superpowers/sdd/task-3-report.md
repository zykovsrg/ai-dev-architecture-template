# Task 3 report — compact project index

## Implementation summary

Task 3 adds one read-only discovery entry point:
`scripts/read-compact-project-index.sh`.
It validates the hub first with the existing registry checker, then prints a
deterministic TSV index sorted by `project_id` with exactly these columns:
`project_id`, `name`, `tags`, `status`, `purpose_brief`.

The smoke suite now covers the new compact index path and the two required
negative sentinels:

- a sentinel in `ai/current-task.md` must not appear in the compact index;
- a sentinel in `Memory entry point` must not appear in the compact index.

The routing spec now names this script as the only pre-confirmation project
discovery interface and keeps full task or knowledge reads behind explicit
project or confirmed-set approval.

## Changed files

- `scripts/read-compact-project-index.sh`
- `scripts/hub-smoke-test.sh`
- `docs/superpowers/specs/2026-08-23-routing-and-search-design.md`

## Security properties

- Reads only registry and card metadata.
- Calls the existing registry validator before any index output.
- Emits only the five approved TSV fields.
- Sorts by `project_id` for stable output.
- Does not print project paths, `ai/current-task.md`, `knowledge/`, code, or
  `Memory entry point`.
- Exits non-zero when the registry is invalid.

## Tests

Already run before the stop request:

- `bash scripts/hub-smoke-test.sh` — passed.
- `bash scripts/hub-smoke-test.sh` after the tab regression fix — passed.
- Focused tab regression repro with a copied fixture whose registry and card
  paths were rewritten to the copied root — passed; exit status was nonzero and
  stdout contained only the header line.
- `bash -n scripts/read-compact-project-index.sh scripts/hub-smoke-test.sh` —
  passed.
- `bash scripts/read-compact-project-index.sh /Users/zykovsrg/Documents/vibecode/_ai-hub | sed -n '1,5p'`
  — showed the expected TSV header and real rows.

Also requested and now completed:

- `git diff --check` — pending this turn.

## Concerns

- The report file itself is not part of the three-file commit the user asked
  for, so it will remain a working-tree change unless explicitly included later.
- The compact index uses the existing registry contract, so any future registry
  shape change will need a matching update in the validator and smoke fixtures.
- The tab regression failure was caused by the copied smoke fixture still
  pointing at the original root, not by the compact index output contract.
