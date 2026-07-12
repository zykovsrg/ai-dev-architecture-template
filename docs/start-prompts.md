# Start prompts

Use these prompts in three common scenarios:

1. first installation of the architecture into a project;
2. moving to a new dialog or another AI agent inside an already connected project;
3. continuing after compressed context, compacted context, or a restored summary.

## Key rules for all prompts

### Protected architecture files and controlled memory files

The full lists of protected files and controlled memory are in [file-roles.md](file-roles.md).

They may be changed only through the appropriate workflow:

- `implementation` — update the current task, Stage, handoff, or an explicitly confirmed future task;
- `task-intake` — record the first task in `ai/current-task.md` or decide whether `task-switch` is needed;
- `task-switch` — pause a task, replace the current one after confirmation, or promote a future task;
- `task-finish` — record the result, important decisions, confirmed future tasks, clear the current task after confirmation, and save the result;
- `architecture-update` — update memory when it is part of a confirmed architecture change.

### Skills

If a task matches a skill's trigger, open the current `ai/skills/*/SKILL.md`. Do not apply a skill from memory.

For UI tasks, open `ui-review` and `write-tests`.

For bugs, crashes, flaky behavior, debug requests, performance tasks, and complex work, use Superpowers when it is available. If Superpowers is not installed, say so and ask whether to install/configure it or continue manually.

For ideas for later, use `ai/future-tasks.md`; there is no separate skill.

For pre-merge or complex review, open `release-check` and check whether `code-review-graph` is needed.

### Context compaction

Compressed context, compacted context, restored summary, and conversation summary continuation count as a new session. Before continuing, `environment-check` is required unless the user explicitly says to skip it.

After `environment-check`, the agent must show a menu of available next commands and skills. The menu is informational: it does not launch workflows automatically.

## 1. First installation of the architecture into a project

For a simple installation or update without a task description, use the [universal start prompt](../README.md#установка-в-проект-универсальный-стартовый-промт) — it is convenient to share as a link.

The prompt below is the extended variant: installation together with setting the first task.

Use it when the architecture is not yet connected to the project.

```text
You are working in the project as an AI coding agent.

I need to install the AI development architecture for the first time from the repository:
https://github.com/zykovsrg/ai-dev-architecture-template

Task description:

Goal:
<insert the project or task goal here>

What needs to be done:
<insert the description of the idea, task, or a prompt prepared by another AI here>

Constraints:
<insert the constraints here: what must not be broken, changed, or overwritten>

How to know it is done:
<insert the completion criteria here>

Task:
1. Check whether the project has AGENTS.md, CLAUDE.md, and the ai/ folder.
2. Do not overwrite existing files without my confirmation.
3. If the architecture is not installed yet, propose a safe installation from the template.
4. If required files are missing after installation, show the list and offer to restore them from the template.
5. After installation, run environment-check.
6. Before the first working task, use task-intake and record the task in ai/current-task.md.
7. Do not install anything extra without my confirmation.
8. Before using an external skill, init workflow, or setup command, first read AGENTS.md or CLAUDE.md.
9. Respect the separation of protected architecture files and controlled memory files.
10. If a workflow from a skill is needed — open the current ai/skills/*/SKILL.md, do not work from memory.

After the check, say:
- what is installed correctly;
- what is missing;
- what needs to be filled in manually;
- whether the architecture is ready for the first task;
- which next commands and skills are available.

The list of next commands and skills is a menu, not an instruction to run everything.

After installation:
- for a new project, first fill in ai/project-context.md and ai/current-task.md;
- ai/current-task.md must have Status and Stage;
- ai/decisions.md, ai/changelog.md, ai/paused-tasks.md, and ai/future-tasks.md may stay as empty templates;
- change ai/external-tools.md only when the list of expected external tools or controlled methodologies changes.

Important rules:
- Communicate with me in Russian.
- I am not a developer; explain technical terms in simple words.
- Do not change application code while installing the architecture.
- Do not make large changes without a plan and confirmation.
- Run bugs and complex tasks through Superpowers when it is available.
- Change protected architecture files only through architecture-update after my explicit confirmation.
- Change controlled memory files only through the appropriate workflow.
```

## 2. Moving to a new dialog or another AI agent inside the project

Use it when the architecture is already installed, but you are opening a new chat or moving to another AI agent.

```text
You are working in a project with the AI development architecture installed:
https://github.com/zykovsrg/ai-dev-architecture-template

Project folder:
<insert the project path>

Task description:

Goal:
<insert the project or task goal here>

What needs to be done:
<insert the description of the idea, task, or a prompt prepared by another AI here>

Constraints:
<insert the constraints here: what must not be broken, changed, or overwritten>

How to know it is done:
<insert the completion criteria here>

First run environment-check. Do not edit anything.

After environment-check, show the available next commands and skills. Do not launch the listed workflows automatically.

Then use task-intake before the working task.

After that, read only:
- AGENTS.md or CLAUDE.md;
- ai/current-task.md.

Do not read the whole ai folder automatically.

If needed to understand the task, additionally open only the relevant files:
- ai/project-context.md;
- ai/decisions.md;
- ai/changelog.md;
- ai/future-tasks.md, if a future task must be saved, found, or promoted;
- the needed ai/skills/*/SKILL.md.

If the current task runs through Superpowers or another plan-driven workflow, additionally open only the relevant files:
- ai/superpowers/specs/<the needed spec>.md;
- ai/superpowers/plans/<the needed plan>.md.

The file ai/superpowers/plans/<the needed plan>.md is the source of truth for progress. Do not rely only on TodoWrite, TaskCreate, TaskUpdate, a summary, or the chat history. After completing a plan item, update the checkbox in the .md plan; on partial completion, add a Note.

If ai/current-task.md contains an active unfinished task:
1. Briefly restate the current task.
2. Name the Mode.
3. Name the Status and Stage.
4. Name the relevant files.
5. Name the Done criteria.
6. Say what the next safe step is.
7. Say whether task-switch is needed.
8. Say whether Superpowers is needed. For bugs and complex tasks, Superpowers is expected when available.

If ai/current-task.md has Status: empty or contains an empty template:
1. Ask me to set the task in the format:
   - Mode
   - Status
   - Stage
   - Goal
   - Relevant files
   - Done criteria

Important rules:
- Communicate with me in Russian.
- I am not a developer; explain technical terms in simple words.
- Do not edit files without my confirmation unless the task requires implementation.
- Before a working task, use task-intake.
- Do not overwrite ai/current-task.md if it contains an unfinished task.
- Change protected architecture files only through architecture-update after my explicit confirmation.
- Change controlled memory files only through the appropriate workflow.
- If I ask for a different task while the current one is unfinished, use task-switch.
- If the task is complete, use task-finish.
- If I ask to save an idea for later, use ai/future-tasks.md.
- Use Superpowers for bugs and complex tasks when it is available; for other tasks — when I explicitly ask or when ai/current-task.md says: Use Superpowers: yes.
```

## 3. Continuing after compressed context or a restored summary

Use it when the previous dialog was compressed, restored from a summary, or carried over into a new context.

```text
You are continuing work in a project with the AI development architecture installed:
https://github.com/zykovsrg/ai-dev-architecture-template

This is a continuation after compressed context / restored summary. Treat it as a new session.

First run environment-check. Do not edit anything.

After environment-check:
1. Show the available next commands and skills. Do not launch the listed workflows automatically.
2. Read AGENTS.md or CLAUDE.md.
3. Read ai/current-task.md.
4. Use task-intake before continuing the working task.
5. If the task is plan-driven, read only the relevant ai/superpowers/plans/<plan>.md and, if needed, the spec.
6. Do not rely only on the summary. Verify the facts through the files.
7. Name the current Mode, Status, Stage, Goal, relevant files, and Done criteria.
8. Check whether the summary diverges from the files.
9. If there is a divergence, treat the files as the source of truth and tell me.
10. If a skill is needed, open the current ai/skills/*/SKILL.md.
11. If the task looks complete, propose task-finish, but do not close it without confirmation and saving the result.

In review mode, do not report a problem as a fact until you have verified it through read, grep, diff, logs, or tests. If unverified — call it a hypothesis.
```
