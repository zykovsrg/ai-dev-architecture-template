# Prompt for the next session — Obsidian phase 2

Project: ai-dev-architecture

Path: /Users/zykovsrg/Documents/vibecode/_ai-hub/projects/ai-dev-architecture

I confirm work in this project. Continue from its files rather than relying on
chat memory.

First run the project session check. Read AGENTS.md, ai/current-task.md,
ai/decisions.md, ai/future-tasks.md, and only the relevant existing specs and
research listed below. Show a concise task snapshot before proposing work.

Foundation is implemented and merged into local main at commit 6f8c622. Its
fresh consistency check, full hub smoke test, and final independent security
review passed. No live hub, Obsidian vault, Apple Calendar, MCP, or external
system has been changed. Foundation remains in review until I explicitly
confirm task-finish.

After task-finish confirmation, promote the Obsidian integration future task
through the normal task workflow. Start with the smallest safe next phase:
read-only inventory of the copied vault and an implementation plan for the
Obsidian projection. If tmp/obsidian-vault-copy/Obsidian is unavailable, ask
me to provide a fresh copy inside the project; do not inspect the original
vault outside the hub's allowed area.

Non-negotiable decisions:

- Project ai/ records and hub-owned archiproject records are canonical.
  Obsidian is a generated local human-facing projection, never a second task
  database.
- An archiproject has projects; a project has at most one
  primary_archiproject. Only archiproject_contribution counts toward progress;
  related_archiprojects never double-count. Contribution 0 is valid.
- Waiting belongs to a task/subtask. A project becomes Waiting only when it
  has no other actionable work.
- The target is one generated Obsidian Kanban board: one card per project,
  embedded next actions, columns Incoming / Planned / Active / Waiting /
  Paused / Completed.
- Project knowledge belongs with the project. Shared knowledge, including a
  meeting relevant to several projects, is stored once in the common knowledge
  base and linked from projects. Use PARA-style Areas, Resources, Inbox, and
  Archives. Inbox is only a fallback for ambiguous captures.
- Commands to design later: plan day, parse meeting, find knowledge; then
  15-minute daily review, Sunday 30-minute archiproject review, and a
  proposal-only session audit.
- Apple Calendar is later and separate: selected test calendar only, preview,
  a new explicit write confirmation, and no deletion.
- Never infer that legacy Obsidian checkboxes or Kanban cards are active tasks.
  Classify them first.
- You may analyse and propose. Before every write of a task, deadline, note,
  Obsidian file, Calendar event, or migration, show the exact proposal and
  ask for fresh explicit confirmation.

Start by reading only:

1. docs/superpowers/research/2026-08-23-current-system-inventory.md
2. docs/superpowers/specs/2026-08-23-unified-assistant-architecture.md
3. docs/superpowers/specs/2026-08-23-work-model-design.md
4. docs/superpowers/specs/2026-08-23-obsidian-projection-design.md
5. docs/superpowers/specs/2026-08-23-assistant-workflows-design.md
6. ai/decisions.md and ai/future-tasks.md

Then give me a short, evidence-based recommendation for the next narrow task.
Do not implement or migrate anything until I approve the design and plan.
