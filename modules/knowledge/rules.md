# Knowledge Module Rules

## Hub-Managed Project Flow

- `hub-knowledge-capture` — creates or updates one explicitly selected record in
  the confirmed project's local `knowledge/` tree after exact confirmation.
- `hub-knowledge-review` — checks one explicit project-local record, folder, or
  task-linked set and waits for exact confirmation before any edit. A task-close
  workflow may offer, but never start, a focused `hub-knowledge-review`.

## Optional Project Knowledge

`knowledge/` is optional local reference material, not default context and not
an automatic conversation archive. A new project receives only the empty
knowledge scaffold as part of its one confirmed `hub-project-create` operation.
Hub-created projects use the central hub-owned `hub-knowledge-capture` and
`hub-knowledge-review` workflows; generic project skills are never copied into
them. Both workflows canonicalize the confirmed project and selected paths,
reject absolute paths, traversal, and symlink components, and keep every record
inside that project's `knowledge/` tree and matching type category.

For an existing confirmed registered hub project, use `hub-knowledge-enable` only
after a separate explicit confirmation that repeats the project ID and exact
registered path. It may inspect only the registry identity and the exact
scaffold paths, must not follow symlinks, and must not read records or unrelated
project content. Its preview names `knowledge/README.md`,
`knowledge/record-template.md`, and all four category directories. After the
matching confirmation, it creates only absent scaffold files and directories;
it never overwrites records or creates project instructions, skills, Git, code,
dependencies, services, registry entries, cards, or active-project changes.
Its preflight uses `lstat`: the confirmed project and category paths must be
real directories, while existing README and record-template paths must be
regular files.

All record workflows prohibit secrets, personal data, and client data and omit
or redact rejected material without echoing it. Reviews validate required
frontmatter, the exact four types and five statuses, record dates, source dates,
contradictions, and type/category agreement. Stale and superseded records stay
at their original paths and link to their replacements; they are never silently
deleted.

Knowledge enablement applies only to existing hub projects. Legacy standalone
migration is out of scope; it neither imports, copies, nor transforms a legacy
knowledge directory.

## Information Updates

For temporary meeting text scoped to one confirmed project, use the
`hub-info-update` workflow.
