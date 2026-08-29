# Current Task

Status: active

Task ID: TASK-20260829-001

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: spec

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Спроектировать слой личного AI-ассистента над хабом: общий обзор дел по всем проектам, разбор входящих материалов и предложение изменений в проектах с обязательным подтверждением перед записью. Отдельно оценить, можно ли упростить текущую механику.

## Use Superpowers

yes

## Relevant files

- `hub-template/AGENTS.md`
- `hub-template/ai/architecture.md`
- `hub-template/ai/skills/hub-project-router/SKILL.md`
- `hub-template/ai/skills/hub-workflows/SKILL.md`
- `hub-template/ai/project-registry.md`

## Done criteria

- Описана целевая модель личного ассистента над всеми проектами.
- Заданы понятные сценарии: обзор дел, разбор встречи и раскладка по проектам.
- Указаны точные правила доступа, предпросмотра и подтверждения.
- Показаны чистый и более дешёвый варианты внедрения.
- Упрощение текущей архитектуры оценено как отдельная опция.

## Agent handoff

Last agent:

What changed:

Open risks:

Next agent should check:
