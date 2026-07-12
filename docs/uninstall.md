# How to remove the architecture

Do not delete the `ai/` folder wholesale without checking it first. It may hold the history of current, paused, and future tasks, project decisions, and the changelog.

Ask the agent: `Help me remove the AI development architecture`.

Before making changes, the agent must:

1. show the files that belong to the architecture;
2. flag files that may contain project content;
3. offer a backup of the task memory;
4. ask whether to remove only the rules or also the task history;
5. show the final removal plan;
6. get a separate confirmation.

The safe default is to remove the architecture rules and skills but keep a copy of `ai/current-task.md`, `ai/paused-tasks.md`, `ai/future-tasks.md`, `ai/project-context.md`, `ai/decisions.md`, and `ai/changelog.md`.

`AGENTS.md`, `CLAUDE.md`, `.claude/`, and `.codex/` may contain more than this architecture's files. The agent must edit them selectively, not delete them wholesale.
