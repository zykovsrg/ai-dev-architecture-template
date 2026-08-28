# Current Task

Status: active

Task ID: FT-20260827-001

Allowed statuses: empty / active / review / blocked / done / paused

Note: `paused` is a transient status used only while `task-switch` is moving this
task into `ai/paused-tasks.md`. After the switch this file holds the new task and
the paused one lives in `ai/paused-tasks.md`.

Stage: planning

Allowed stages: intake / spec / planning / implementation / review / task-finish

## Mode

architecture-update

## Goal

Реализовать три улучшения knowledge-слоя: происхождение записи (`origin`),
корзину для слабых сигналов и дату начала действия (`valid_from`).

## Use Superpowers

yes

## Relevant files

- knowledge/record-template.md
- knowledge/README.md
- ai/skills/knowledge-capture/SKILL.md
- ai/skills/knowledge-review/SKILL.md
- template/

## Done criteria

- В шаблоне есть `origin` со значениями `stated`, `inferred`, `observation` и
  поле `valid_from`; оба поля описаны в README.
- `knowledge-capture` требует осознанно выбрать `origin`.
- `knowledge-review` отдельно показывает записи с `origin: inferred`.
- Для слабых сигналов определены место хранения и правила разбора.
- Корень и `template/` синхронизированы; проходит
  `bash scripts/check-consistency.sh`.

## Agent handoff

Last agent: Codex

What changed: FT-20260827-001 повышена из future task в текущую; пользователь выбрал полный вариант из трёх пунктов.

Open risks: Нужно сохранить изоляцию проектов и не продублировать назначение cross-project signals.

Next agent should check: Утверждённую спецификацию и план реализации knowledge-слоя.
