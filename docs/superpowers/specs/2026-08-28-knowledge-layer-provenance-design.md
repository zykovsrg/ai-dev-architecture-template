# Knowledge Layer Provenance and Inbox Design

## Goal

Make the project knowledge base distinguish evidence from model inference,
preserve weak observations safely, and express when a durable rule starts to
apply.

## Scope

The change applies to the standalone project template and its root source:

- `knowledge/record-template.md` and `template/knowledge/record-template.md`;
- `knowledge/README.md` and `template/knowledge/README.md`;
- `ai/skills/knowledge-capture/SKILL.md` and its template copy;
- `ai/skills/knowledge-review/SKILL.md` and its template copy;
- knowledge scaffolding and its installation tests.

`hub-template/` is not changed: its knowledge workflows operate on the selected
project's local `knowledge/` directory and do not own the standalone record
format.

## Data model

Every durable knowledge record receives two frontmatter fields:

```yaml
origin: stated
valid_from: null
```

`origin` is required and has exactly three values:

- `stated` — the user or a cited source provided the claim directly;
- `inferred` — an agent derived the claim from available context;
- `observation` — an unconfirmed signal that must not be treated as knowledge.

`valid_from` is either `null` or a real `YYYY-MM-DD` date. It says when the
record's rule or claim begins to apply; `created` remains the date the Markdown
file was created.

## Inbox

Each project has an optional `knowledge/inbox/` directory. It is a holding area
for files with `origin: observation`. It is not a fifth knowledge category and
does not change the four durable categories: `research`, `decisions`, `risks`,
and `runbooks`.

`knowledge-capture` writes a weak signal to the inbox only after the existing
exact-path confirmation. It must not silently promote, copy, or discard it.

`knowledge-review` can review an explicitly selected inbox file or folder. It
reports three possible actions: promote it into one selected durable category
with a chosen `origin`; retain it in the inbox; or delete it as unhelpful.
Every action needs the existing exact user confirmation. A promoted observation
is moved rather than copied, so one claim has one canonical location.

## Workflow behavior

Capture requires an explicit `origin` choice. It never defaults to `stated`.
When `origin: observation` is selected, capture requires a target below
`knowledge/inbox/`; all other origins require one of the four durable category
directories. Existing containment, secret, privacy, status, and path checks
remain in force.

Review validates `origin` and `valid_from` alongside the current frontmatter.
Its report groups inferred records separately from stated records and flags an
observation outside the inbox as invalid. Inbox review reports its proposed
disposition but does not mutate anything before confirmation.

## Boundaries and errors

- `ai/cross-project-signals.md` remains a hub-only store for sanitised,
  explicitly approved links between projects. It is not an inbox.
- An invalid `origin`, invalid `valid_from`, or inbox record outside the inbox
  is a review defect.
- An inbox entry cannot be silently converted to durable knowledge.
- The new directory follows the existing containment rules and rejects
  symlinks, absolute paths, traversal, secrets, personal data, and client data.

## Verification

Tests will prove that scaffolding includes the inbox, installation creates it,
the standalone and template copies match, and the workflow text contains the
new validation and confirmation rules. The full regression commands are
`bash scripts/check-consistency.sh` and `bash scripts/smoke-test.sh`.
