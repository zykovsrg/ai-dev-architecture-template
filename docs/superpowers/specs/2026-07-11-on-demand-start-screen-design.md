# On-Demand Start Screen Design

Date: 2026-07-11

## Goal

Add a short, plain-language start screen that explains the AI development
architecture to a non-developer and shows the project's current work state.
The screen appears only after an explicit user request. It must not appear
automatically at session boundaries or during a normal `environment-check`.

## User Requests That Activate It

The dedicated `start-screen` skill activates for explicit requests such as:

- "Покажи стартовый экран";
- "С чего начать?";
- "Как работать с архитектурой?";
- "Что умеет эта архитектура?".

An explicit request for a full skill or tool catalog is separate. The start
screen gives only categories and important examples, then offers a command for
the full catalog.

## Start Screen Content

The response uses concise Russian information style and avoids developer jargon.
It contains six short sections:

1. **What this is** — what the architecture helps the user accomplish.
2. **How work is organized** — project memory, one current task, paused work,
   future ideas, and confirmed task completion.
3. **Where to start** — four to six useful commands.
4. **What is available** — compact categories of project skills, external
   skills, tools, and controlled methodologies. Do not print a full catalog.
5. **How to remove it** — tell the user to request removal, review the planned
   file list, choose whether to preserve task memory, and confirm destructive
   actions. Never remove files from the start-screen workflow itself.
6. **Current project state** — current task goal, `Status`, `Stage`, and the next
   step or blocker. If no task is active, say so and suggest `task-intake`.

The target is approximately one normal screen of text. Prefer short paragraphs
and compact bullets. Do not repeat the full `environment-check` report.

## Architecture

Create a required base skill at `ai/skills/start-screen/SKILL.md`. It owns the
activation rules, required reads, content template, and safety rules.

The skill reads:

- `ai/current-task.md` for the live task snapshot;
- `ai/future-tasks.md` only for a compact future-work count or useful prompt;
- `ai/external-tools.md` for the configured external tool categories;
- the available skill catalog or project skill directory for concise categories.

The skill is read-only. It must not run `task-intake`, `task-switch`,
`task-finish`, installation, or removal automatically.

## Relationship to Environment Check

Keep the existing session-boundary rule unchanged: `environment-check` still
runs when the architecture enters a new logical session, including restored or
compacted context.

The start screen is independent:

- it never appears automatically;
- a repeated `environment-check` does not show it;
- requesting the start screen does not require rerunning `environment-check`;
- the screen may summarize the latest task state but is not an environment
  availability audit.

## Layered Storage and Token Impact

Keep `AGENTS.md` and `CLAUDE.md` short. Add only one equivalent routing line to
each file pointing explicit start/help requests to the new skill. The expected
growth is no more than 42 bytes per file, below one percent of their current
size.

Store the detailed workflow in `ai/skills/start-screen/SKILL.md`. Add the
high-level behavior to `ai/architecture.md`. Mirror installed-project files in
`template/` so new installations receive the same behavior.

Update required-skill checks and user documentation only where the new base
skill must be discoverable or verified. Avoid copying the full start-screen
text into multiple files.

## Removal Guidance

The screen provides guidance, not an uninstall command. Removal is a separate,
explicitly confirmed architecture operation because project repositories may
contain user-owned content inside files or directories also used by the
architecture.

Before removal, the agent must:

1. inventory architecture-owned files and any mixed-ownership files;
2. show the proposed changes;
3. offer to preserve or back up controlled task memory;
4. distinguish removing architecture rules from deleting task history;
5. obtain explicit confirmation before destructive edits.

A concise uninstall guide may be added to documentation, but an automatic
destructive script is outside this task's scope.

## Documentation and Template Synchronization

Update the canonical repository and matching template copies. Expected areas:

- `AGENTS.md` and `CLAUDE.md` plus template copies;
- `ai/architecture.md` plus template copy;
- new `ai/skills/start-screen/SKILL.md` plus template copy;
- `ai/skills/environment-check/SKILL.md` plus template copy for the required
  base-skill presence check only;
- concise installation or command documentation where base skills are listed;
- smoke tests and consistency checks that verify the new skill is installed.

## Verification

Verify these scenarios:

1. An explicit start/help request produces the short screen.
2. A normal session-start `environment-check` does not produce the start screen.
3. An active task appears with goal, status, stage, and next step.
4. An empty task state suggests `task-intake`.
5. The screen provides categories rather than a full skill catalog.
6. Removal wording requires preview, memory choice, and confirmation.
7. Root and template architecture files remain synchronized.
8. Installation smoke tests include the new skill.
9. `AGENTS.md` and `CLAUDE.md` remain equal in meaning and grow by less than one
   percent where practical.

## Risks and Mitigations

- **Screen becomes a second manual:** enforce a one-screen target and route full
  catalogs to separate requests.
- **Duplicate environment output:** keep the two workflows independent.
- **Stale lists:** describe categories and derive availability from the current
  environment instead of hardcoding every external skill.
- **Unsafe removal:** provide guidance only and require a separate confirmed
  architecture update for deletion.
- **Entry-file growth:** keep detailed instructions in the skill and add only a
  routing line to each entry file.

## Out of Scope

- Automatic display at new-session boundaries.
- A graphical user interface.
- An automatic uninstall script.
- Installing or removing external skills and tools.
- Changing the existing meaning of a logical session boundary.
