# Task 1 report: group-only archiproject records

## Implementation summary

Added conditional archiproject validation for exactly one `kind`:

- `group` requires `id`, `name`, `status`, `kind` and rejects `target`, `unit`,
  and `due`.
- `goal` requires all six fields and keeps numeric target/date validation.
- Group primaries require `archiproject_contribution: none`; goal primaries
  retain nonnegative numeric contributions.
- Added positive and negative smoke fixtures for group records, forbidden group
  metrics, missing goal target, and unknown kind.
- Documented both YAML forms and recorded the overview grouping decision.

## Files

- `scripts/check-hub-registry.sh`
- `scripts/hub-smoke-test.sh`
- `hub-template/ai/archiprojects.md`
- `template/ai/decisions.md`

## RED/GREEN commands and relevant output

RED (after adding the group fixture, before implementation):

```text
$ bash scripts/hub-smoke-test.sh
ERROR: unrecognized YAML line in archiproject registry entry: hadassah
```

GREEN (after implementation):

```text
$ bash scripts/hub-smoke-test.sh
Sentinel evidence: validator output and xtrace contain neither the marker nor the named forbidden file paths.
Unregistered-directory evidence: warned on stderr, exit code and stdout summary unchanged.
Malicious traversal evidence: lexical and symlink card escapes were rejected before the card-content check; sentinel markers were absent from output and xtrace.
Scale fixture: 5 projects, 1059/2400 bytes
```

## Tests

- `bash scripts/hub-smoke-test.sh` — passed.
- `bash -n scripts/check-hub-registry.sh scripts/hub-smoke-test.sh` — passed.
- `git diff --check` — passed.

## Self-review

The parser still rejects unknown YAML keys, duplicate fields, malformed goal
values, and duplicate registry IDs. Group records never expose fake metrics.
The smoke fixture confirms group metadata can use `none` contribution while
existing numeric goal and no-primary cases remain covered.

## Concerns

No known concerns.
