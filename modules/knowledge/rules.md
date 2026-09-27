# Knowledge Module Rules

## Hub-Managed Project Flow

- `hub-knowledge-capture` — creates or updates one explicitly selected record in
  the confirmed project's local `knowledge/` tree after exact confirmation.
- `hub-knowledge-review` — checks one explicit project-local record, folder, or
  task-linked set and waits for exact confirmation before any edit.

## Optional Project Knowledge

`knowledge/` is optional local reference material, not default context and not
an automatic conversation archive. A new project receives only the empty
knowledge scaffold as part of its one confirmed project-creation operation
(see `## after-project-create`).
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

## before-task-close

When a task closure fires `before-task-close` and durable records linked from
this task may need a focused check, the agent may offer `hub-knowledge-review`,
but must never start it automatically. Declining it has no effect on closure.
The offer does not authorize reading or writing knowledge records.

## after-project-create

When project creation fires `after-project-create`, add this block to the same
creation preview:

```text
Knowledge scaffold:
- <canonical-path>/knowledge/README.md
- <canonical-path>/knowledge/record-template.md
- <canonical-path>/knowledge/research/
- <canonical-path>/knowledge/decisions/
- <canonical-path>/knowledge/risks/
- <canonical-path>/knowledge/runbooks/
- <canonical-path>/knowledge/inbox/
```

After the creation confirmation, create only the absent scaffold at
`<canonical-path>/knowledge/`: `README.md`, `record-template.md`, and the empty
`research/`, `decisions/`, `risks/`, `runbooks/`, and `inbox/` directories.
Inbox holds weak observations and is not a durable category. Write the two
files with the canonical contents in
`ai/skills/hub-knowledge-enable/SKILL.md` § Canonical scaffold files. Never
overwrite records or any existing scaffold file. The created project uses the
hub-owned `hub-knowledge-capture` and `hub-knowledge-review` workflows; do not
copy them into it.
